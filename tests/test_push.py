"""Push notifications: the device store, the APNs client and the API that triggers them."""

import base64
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from api.push import ApnsClient, ApnsConfig, PushNotifier, provider_token
from geo_draw.ai_codegen import AiSettings
from geo_draw.devices import PRODUCTION, SANDBOX, Device, DeviceStore

from tests.test_api import ApiTestCase, EQUATION, TRIANGLE, read_events

TOKEN = "ab" * 32
OTHER_TOKEN = "cd" * 32


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _config() -> ApnsConfig:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    return ApnsConfig("KEY123", "TEAM456", pem, "com.mathmate.app")


class DeviceStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = DeviceStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_token_moves_to_whoever_registers_it_last(self):
        self.store.register("guest:1", TOKEN, environment=SANDBOX)
        self.store.register("user-a", TOKEN)
        self.assertEqual(self.store.for_owner("guest:1"), [])
        self.assertEqual(self.store.for_owner("user-a"),
                         [Device(TOKEN, "user-a", "ios", PRODUCTION)])
        self.store.remove(TOKEN, "someone-else")  # not theirs: kept
        self.assertEqual(len(self.store.for_owner("user-a")), 1)
        self.store.register("user-a", OTHER_TOKEN)
        self.store.delete_owner("user-a")
        self.assertEqual(self.store.for_owner("user-a"), [])


class ApnsClientTests(unittest.TestCase):
    def test_provider_token_is_a_valid_es256_jwt(self):
        config = _config()
        token = provider_token(config, 1_700_000_000)
        header, claims, signature = token.split(".")
        self.assertEqual(json.loads(_unb64(header)), {"alg": "ES256", "kid": "KEY123"})
        self.assertEqual(json.loads(_unb64(claims)), {"iss": "TEAM456", "iat": 1_700_000_000})
        raw = _unb64(signature)
        der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        public = serialization.load_pem_private_key(config.private_key_pem.encode(), None).public_key()
        public.verify(der, f"{header}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if bad

    def test_send_and_dead_tokens_are_forgotten(self):
        requests = []

        def apns(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith(OTHER_TOKEN):
                return httpx.Response(410, json={"reason": "Unregistered"})
            return httpx.Response(200)

        with tempfile.TemporaryDirectory() as tmp:
            devices = DeviceStore(Path(tmp))
            devices.register("user-a", TOKEN, environment=SANDBOX)
            devices.register("user-a", OTHER_TOKEN)
            notifier = PushNotifier(devices, ApnsClient(_config(), httpx.MockTransport(apns)))
            notifier.notify("user-a", "Hình vẽ đã xong", "Tam giác ABC",
                            {"conversation_id": "c1", "kind": "figure"}, thread_id="c1")
            notifier.flush()
            notifier.close()
            self.assertEqual([d.token for d in devices.for_owner("user-a")], [TOKEN])

        sandbox = next(r for r in requests if r.url.path.endswith(TOKEN))
        self.assertEqual(sandbox.url.host, "api.sandbox.push.apple.com")
        self.assertEqual(sandbox.headers["apns-topic"], "com.mathmate.app")
        self.assertEqual(sandbox.headers["apns-push-type"], "alert")
        self.assertTrue(sandbox.headers["authorization"].startswith("bearer "))
        self.assertEqual(json.loads(sandbox.content), {
            "aps": {"alert": {"title": "Hình vẽ đã xong", "body": "Tam giác ABC"},
                    "sound": "default", "thread-id": "c1"},
            "conversation_id": "c1", "kind": "figure"})
        production = next(r for r in requests if r.url.path.endswith(OTHER_TOKEN))
        self.assertEqual(production.url.host, "api.push.apple.com")


class FakeApns:
    def __init__(self):
        self.sent: list[tuple[Device, dict]] = []

    def send(self, device, payload, collapse_id=None):
        self.sent.append((device, payload))

    def close(self):
        pass


class PushApiTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 50, 50

    def setUp(self):
        super().setUp()
        self.apns = FakeApns()
        self.state.push = PushNotifier(self.state.devices, self.apns)

    def app_client(self, token: str | None = None):
        client = self.client()
        client.headers["X-Client"] = "ios"
        if token:
            client.headers["Authorization"] = f"Bearer {token}"
        return client

    def wait_for_jobs(self):
        self.state.jobs.shutdown(wait=True)
        self.state.push.flush()

    def test_register_and_remove_a_device(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token)
        user_id = client.get("/api/auth/me").json()["user"]["id"]
        self.assertEqual(client.post("/api/devices", json={"token": "nope"}).status_code, 422)
        response = client.post("/api/devices", json={"token": TOKEN.upper(), "environment": "sandbox"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.state.devices.for_owner(user_id),
                         [Device(TOKEN, user_id, "ios", SANDBOX)])
        self.assertEqual(self.app_client().delete(f"/api/devices/{TOKEN}").status_code, 204)
        self.assertEqual(len(self.state.devices.for_owner(user_id)), 1)  # a stranger cannot
        self.assertEqual(client.delete(f"/api/devices/{TOKEN}").status_code, 204)
        self.assertEqual(self.state.devices.for_owner(user_id), [])

    def test_a_reply_nobody_watched_is_pushed(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token)
        client.post("/api/devices", json={"token": TOKEN})
        conversation_id = self.send(client, EQUATION).json()["conversation"]["id"]
        self.wait_for_jobs()  # the app was in the background: nobody read the events
        [(device, payload)] = self.apns.sent
        self.assertEqual(device.token, TOKEN)
        self.assertEqual(payload["aps"]["alert"], {"title": "MathMate đã trả lời",
                                                   "body": "Tên bài toán"})
        self.assertEqual((payload["conversation_id"], payload["kind"]), (conversation_id, "chat"))

    def test_a_finished_figure_is_pushed(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token)
        self.use_parser(client)
        client.post("/api/devices", json={"token": TOKEN})
        started = self.send(client, TRIANGLE).json()
        read_events(client, started["job_id"])  # the app watched the tutor, not the drawing
        self.wait_for_jobs()
        [(_, payload)] = self.apns.sent
        self.assertEqual((payload["aps"]["alert"]["title"], payload["kind"]),
                         ("Hình vẽ đã xong", "figure"))

    def test_a_watched_reply_is_not_pushed(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token)
        client.post("/api/devices", json={"token": TOKEN})
        for _ in range(3):
            read_events(client, self.send(client, EQUATION).json()["job_id"])
        self.wait_for_jobs()
        self.assertEqual(self.apns.sent, [])

    def test_deleting_the_account_forgets_its_devices(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token)
        user_id = client.get("/api/auth/me").json()["user"]["id"]
        client.post("/api/devices", json={"token": TOKEN})
        client.request("DELETE", "/api/auth/me", json={"password": "hinhhoc1"})
        self.assertEqual(self.state.devices.for_owner(user_id), [])
