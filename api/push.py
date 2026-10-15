"""Push notifications to the iOS app through APNs (Apple Push Notification service).

A job that ends while nobody follows its event stream (the app is in the background or
closed) notifies the owner's phones: the tutor answered, or the figure is drawn. The app
hides the banner itself when that conversation is open on screen, so a job that ends just
before the app connects does no harm.

APNs needs a token-based key from the Apple Developer account (Keys → Apple Push Notifications
service, a ``.p8`` file): ``APNS_KEY_ID``, ``APNS_TEAM_ID``, the key itself in
``APNS_KEY_PATH`` (or its PEM text in ``APNS_KEY``, with ``\\n`` for line breaks) and the
app's bundle id in ``APNS_TOPIC``. Without them nothing is sent.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from geo_draw.devices import SANDBOX, Device, DeviceStore

log = logging.getLogger("mathmate.push")

APNS_HOSTS = {SANDBOX: "https://api.sandbox.push.apple.com",
              "production": "https://api.push.apple.com"}
# Apple refuses tokens older than an hour and throttles new ones more often than every 20 min.
TOKEN_LIFETIME = 45 * 60
# APNs answers these when a token will never work again (app removed, wrong environment…).
DEAD_TOKEN_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}


@dataclass(frozen=True)
class ApnsConfig:
    key_id: str
    team_id: str
    private_key_pem: str
    topic: str  # the app's bundle id

    @classmethod
    def from_env(cls) -> ApnsConfig | None:
        key_id, team_id = os.environ.get("APNS_KEY_ID"), os.environ.get("APNS_TEAM_ID")
        topic = os.environ.get("APNS_TOPIC")
        pem = os.environ.get("APNS_KEY", "").replace("\\n", "\n")
        path = os.environ.get("APNS_KEY_PATH")
        if not pem and path:
            try:
                pem = Path(path).read_text()
            except OSError as exc:
                log.error("Không đọc được khóa APNs %s: %s", path, exc)
                return None
        if not (key_id and team_id and topic and pem):
            return None
        return cls(key_id, team_id, pem, topic)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def provider_token(config: ApnsConfig, issued_at: int) -> str:
    """The ES256 JWT that APNs expects in ``authorization: bearer``."""
    key = serialization.load_pem_private_key(config.private_key_pem.encode(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("Khóa APNs phải là khóa EC (.p8).")
    header = _b64url(json.dumps({"alg": "ES256", "kid": config.key_id}).encode())
    claims = _b64url(json.dumps({"iss": config.team_id, "iat": issued_at}).encode())
    signing_input = f"{header}.{claims}".encode()
    r, s = decode_dss_signature(key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")  # JWS wants raw r||s
    return f"{header}.{claims}.{_b64url(signature)}"


class ApnsClient:
    """Sends one notification at a time over a kept-alive HTTP/2 connection."""

    def __init__(self, config: ApnsConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._transport = transport
        self._clients: dict[str, httpx.Client] = {}
        self._token: tuple[str, float] | None = None
        self._lock = threading.Lock()

    def _bearer(self) -> str:
        now = time.time()
        if self._token is None or now - self._token[1] > TOKEN_LIFETIME:
            self._token = (provider_token(self.config, int(now)), now)
        return self._token[0]

    def _client(self, environment: str) -> httpx.Client:
        if environment not in self._clients:
            options = ({"transport": self._transport} if self._transport
                       else {"http2": True})
            self._clients[environment] = httpx.Client(
                base_url=APNS_HOSTS.get(environment, APNS_HOSTS["production"]),
                timeout=10, **options)
        return self._clients[environment]

    def send(self, device: Device, payload: dict, collapse_id: str | None = None) -> str | None:
        """Send to one device. Returns APNs' reason when it refused, else None."""
        headers = {"authorization": f"bearer {self._bearer()}", "apns-topic": self.config.topic,
                   "apns-push-type": "alert", "apns-priority": "10"}
        if collapse_id:
            headers["apns-collapse-id"] = collapse_id[:64]
        with self._lock:
            response = self._client(device.environment).post(
                f"/3/device/{device.token}", headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            return None
        try:
            return response.json().get("reason") or str(response.status_code)
        except ValueError:
            return str(response.status_code)

    def close(self) -> None:
        for client in self._clients.values():
            client.close()


class PushNotifier:
    """Notifies an owner's phones in a background thread, so a slow APNs never holds a job."""

    def __init__(self, devices: DeviceStore, client: ApnsClient | None):
        self.devices = devices
        self.client = client
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="push")

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def notify(self, owner: str, title: str, body: str, data: dict,
               thread_id: str | None = None) -> None:
        if self.client is None:
            return
        self._executor.submit(self._send_all, owner, title, body, data, thread_id)

    def _send_all(self, owner: str, title: str, body: str, data: dict,
                  thread_id: str | None) -> None:
        aps: dict = {"alert": {"title": title, "body": body}, "sound": "default"}
        if thread_id:
            aps["thread-id"] = thread_id
        payload = {"aps": aps, **data}
        for device in self.devices.for_owner(owner):
            try:
                reason = self.client.send(device, payload, collapse_id=thread_id)
            except httpx.HTTPError as exc:
                log.warning("Không gửi được thông báo APNs: %s", exc)
                continue
            if reason in DEAD_TOKEN_REASONS:
                self.devices.remove(device.token, device.owner)
            elif reason:
                log.warning("APNs từ chối thông báo: %s", reason)

    def flush(self) -> None:
        """Wait for the notifications already queued (tests)."""
        self._executor.submit(lambda: None).result()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self.client:
            self.client.close()
