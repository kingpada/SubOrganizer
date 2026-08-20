from __future__ import annotations

import time

from reddit_exporter.gui.workers import WorkerRunner


def test_worker_runner_prevents_double_trigger() -> None:
    runner = WorkerRunner()

    def work():
        time.sleep(0.05)
        return 1

    runner.run(work)
    try:
        runner.run(work)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError:
        pass

    time.sleep(0.1)
    result = runner.poll()
    assert result is not None and result.ok and result.value == 1
