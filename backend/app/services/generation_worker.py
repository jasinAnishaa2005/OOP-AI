"""Per-process safety net that resumes exam generations lost to a crash, restart or deploy.

New exams still start immediately through FastAPI background tasks; this loop only picks up exams that the
database shows as abandoned, so it adds no extra AI calls in normal operation."""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.ai import get_exam_generator
from app.config import get_settings
from app.core.rate_limit import limiter
from app.services.exam_generation import recover_stuck_exams, run_generation

logger = logging.getLogger(__name__)


class GenerationRecovery:
    def __init__(self) -> None:
        settings = get_settings()
        self.interval = settings.generation_recovery_interval_seconds
        self._pool = ThreadPoolExecutor(max_workers=settings.generation_workers, thread_name_prefix="exam-recovery")
        self._stop = threading.Event()
        self._in_flight: set[uuid.UUID] = set()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, name="exam-recovery-sweeper", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._pool.shutdown(wait=False, cancel_futures=True)

    def sweep(self) -> list[uuid.UUID]:
        submitted = []
        for exam_id in recover_stuck_exams():
            with self._lock:
                if exam_id in self._in_flight:
                    continue
                self._in_flight.add(exam_id)
            self._pool.submit(self._run, exam_id)
            submitted.append(exam_id)
        limiter.purge_expired()
        return submitted

    def _run(self, exam_id: uuid.UUID) -> None:
        try:
            run_generation(exam_id, get_exam_generator())
        except Exception:
            logger.exception("Exam %s: recovery run could not start", exam_id)
        finally:
            with self._lock:
                self._in_flight.discard(exam_id)

    def _loop(self) -> None:
        while True:
            try:
                self.sweep()
            except Exception:
                logger.exception("Exam recovery sweep failed")
            if self._stop.wait(self.interval):
                return
