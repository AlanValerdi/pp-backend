import asyncio
import logging

from app.modules.scraper import tracing


async def test_trace_ids_are_task_local(caplog):
    logger = logging.getLogger(__name__)

    async def worker(identifier):
        with tracing.trace_scope(identifier):
            await asyncio.sleep(0)
            tracing.event(logger, identifier)
            assert tracing.trace_id.get() == identifier

    with caplog.at_level("INFO"):
        await asyncio.gather(worker("run-1"), worker("preview-2"))
    assert "trace_id=run-1 event=run-1" in caplog.text
    assert "trace_id=preview-2 event=preview-2" in caplog.text
    assert tracing.trace_id.get() == "-"


def test_progress_is_bounded_and_counts_failures(caplog, monkeypatch):
    now = 0
    monkeypatch.setattr(tracing, "monotonic", lambda: now)
    with caplog.at_level("INFO"):
        progress = tracing.DetailProgress(logging.getLogger(__name__), 52)
        for i in range(52):
            if i == 2:
                now = 11
            progress.complete(i != 3)
    messages = [record.message for record in caplog.records if "event=details_progress" in record.message]
    assert len(messages) == 4
    assert "completed=52" in messages[-1]
    assert "parsed=51" in messages[-1]
    assert "failed=1" in messages[-1]
    assert "remaining_seconds=0.0" in messages[-1]
