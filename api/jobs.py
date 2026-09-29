"""Background drawing jobs and their progress events (read by the SSE endpoint).

A job runs in a small thread pool, so at most ``workers`` Manim renders run at once.
Its results are saved to the conversation store by the job itself, so closing the
browser tab does not lose a drawing; events only drive the live progress display.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

KEEP_FINISHED_SECONDS = 3600

Push = Callable[[str, object], None]


class Job:
    def __init__(self, owner: str):
        self.id = uuid.uuid4().hex
        self.owner = owner
        self.events: list[tuple[str, object]] = []
        self.finished_at: float | None = None
        self._condition = threading.Condition()

    def push(self, kind: str, data: object) -> None:
        with self._condition:
            self.events.append((kind, data))
            if kind in ("done", "error"):
                self.finished_at = time.time()
            self._condition.notify_all()

    def wait(self, start: int, timeout: float) -> tuple[list[tuple[str, object]], bool]:
        """Block until there are events after ``start`` (or the job ended, or timeout)."""
        with self._condition:
            self._condition.wait_for(
                lambda: len(self.events) > start or self.finished_at is not None, timeout
            )
            return self.events[start:], self.finished_at is not None


class JobManager:
    def __init__(self, workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="draw")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, owner: str, work: Callable[[Push], None]) -> Job:
        job = Job(owner)
        with self._lock:
            self._forget_old()
            self._jobs[job.id] = job
        self._executor.submit(self._run, job, work)
        return job

    def get(self, job_id: str, owner: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
        return job if job and job.owner == owner else None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _run(job: Job, work: Callable[[Push], None]) -> None:
        try:
            work(job.push)
        except Exception:  # noqa: BLE001 — report any failure to the waiting browser
            logger.exception("Drawing job %s failed", job.id)
            job.push("error", {"detail": "Máy chủ gặp lỗi khi vẽ hình. Hãy thử lại."})
        else:
            job.push("done", {})

    def _forget_old(self) -> None:
        cutoff = time.time() - KEEP_FINISHED_SECONDS
        for job_id in [job_id for job_id, job in self._jobs.items()
                       if job.finished_at and job.finished_at < cutoff]:
            del self._jobs[job_id]
