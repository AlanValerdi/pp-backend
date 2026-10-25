import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic

trace_id: ContextVar[str] = ContextVar("scrape_trace_id", default="-")


@contextmanager
def trace_scope(identifier: str) -> Iterator[None]:
    token = trace_id.set(identifier)
    try:
        yield
    finally:
        trace_id.reset(token)


def event(logger: logging.Logger, name: str, level: int = logging.INFO, **fields: object) -> None:
    # Callers pass identifiers and counters, never response bodies or contact details.
    values = " ".join(f"{key}={value!r}" for key, value in fields.items())
    logger.log(level, "trace_id=%s event=%s %s", trace_id.get(), name, values)


class DetailProgress:
    def __init__(self, logger: logging.Logger, total: int) -> None:
        self.logger = logger
        self.total = total
        self.completed = self.parsed = self.failed = 0
        self.started = self.last_logged = monotonic()
        event(logger, "details_started", total=total)

    def complete(self, successful: bool) -> None:
        self.completed += 1
        self.parsed += int(successful)
        self.failed += int(not successful)
        now = monotonic()
        if (
            self.completed == 1
            or self.completed % 50 == 0
            or now - self.last_logged >= 10
            or self.completed == self.total
        ):
            elapsed = now - self.started
            event(
                self.logger,
                "details_progress",
                completed=self.completed,
                total=self.total,
                parsed=self.parsed,
                failed=self.failed,
                elapsed_seconds=round(elapsed, 2),
                remaining_seconds=round(elapsed / self.completed * (self.total - self.completed), 2),
            )
            self.last_logged = now
