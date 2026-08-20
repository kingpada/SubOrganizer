from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkerResult:
    ok: bool
    value: Any = None
    error: Exception | None = None


class WorkerRunner:
    def __init__(self) -> None:
        self._active = False
        self._queue: Queue[WorkerResult] = Queue()
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._active

    def run(self, fn: Callable[[], Any]) -> None:
        with self._lock:
            if self._active:
                raise RuntimeError("An operation is already running")
            self._active = True

        def target() -> None:
            try:
                self._queue.put(WorkerResult(ok=True, value=fn()))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(WorkerResult(ok=False, error=exc))
            finally:
                with self._lock:
                    self._active = False

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def poll(self) -> WorkerResult | None:
        try:
            result = self._queue.get_nowait()
        except Empty:
            return None
        return result
