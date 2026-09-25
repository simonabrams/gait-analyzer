"""
Per-step wall-clock timing for the video workers. One summary line per job in
the worker log (Render -> gait-worker -> Logs, search "pipeline_timing"), so a
config change like GAIT_TARGET_FPS / GAIT_REAR_TARGET_FPS can be judged by
where the time actually goes, not just Celery's "succeeded in Ns" total.

Timings and video properties only (frame counts, fps) — no body data, and it
goes to logs, not analytics.
"""

import logging
import time
from contextlib import contextmanager


class StepTimer:
    def __init__(self):
        self._start = time.perf_counter()
        self.steps: dict[str, float] = {}
        self.info: dict[str, object] = {}

    @contextmanager
    def step(self, name: str):
        """Time a block; repeated names accumulate (e.g. per-chunk pose extraction)."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.add(name, time.perf_counter() - t0)

    def add(self, name: str, seconds: float) -> None:
        self.steps[name] = self.steps.get(name, 0.0) + seconds

    def total(self) -> float:
        return time.perf_counter() - self._start

    def summary(self) -> str:
        parts = [f"total={self.total():.1f}s"]
        parts += [f"{name}={secs:.1f}s" for name, secs in self.steps.items()]
        parts += [
            f"{key}={val:.1f}" if isinstance(val, float) else f"{key}={val}"
            for key, val in self.info.items()
        ]
        return " ".join(parts)

    def log(self, logger: logging.Logger, view: str, run_id: str, status: str) -> None:
        logger.info("pipeline_timing view=%s run_id=%s status=%s %s", view, run_id, status, self.summary())
