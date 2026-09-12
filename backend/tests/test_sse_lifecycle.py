import asyncio

from app.api.events import stream_events
from app.core.events import build_event, event_bus


class FakeRequest:
    def __init__(self, disconnected: bool = False):
        self.disconnected = disconnected

    async def is_disconnected(self):
        return self.disconnected


def test_stream_disconnect_unsubscribes_generator():
    async def run():
        event_bus.reset()
        request = FakeRequest()
        response = await stream_events(request, heartbeat_ms=200)
        iterator = response.body_iterator

        first = await iterator.__anext__()
        assert "event: heartbeat" in first
        assert event_bus.subscriber_count() == 1

        request.disconnected = True
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            pass
        assert event_bus.subscriber_count() == 0

    asyncio.run(run())


def test_stream_shutdown_exits_and_removes_subscriber():
    async def run():
        event_bus.reset()
        response = await stream_events(FakeRequest(), heartbeat_ms=200)
        iterator = response.body_iterator
        await iterator.__anext__()
        assert event_bus.subscriber_count() == 1

        event_bus.close_all()
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            pass
        assert event_bus.subscriber_count() == 0

    asyncio.run(run())


def test_stream_delivers_event_without_refresh_heartbeat():
    async def run():
        event_bus.reset()
        response = await stream_events(FakeRequest(), heartbeat_ms=200, max_events=2)
        iterator = response.body_iterator
        first = await iterator.__anext__()
        assert '"event_type":"heartbeat"' in first

        event_bus.publish(build_event("plan.approved", "Plan approved"))
        second = await iterator.__anext__()
        assert "event: plan.approved" in second
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            pass
        assert event_bus.subscriber_count() == 0

    asyncio.run(run())