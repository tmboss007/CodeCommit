import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.events import build_event, event_bus, format_sse

router = APIRouter(prefix="/api/events", tags=["events"])

_DISCONNECT_POLL = 1.0


def _sse_enabled() -> bool:
    return str(getattr(settings, "SSE_ENABLED", "true")).lower() in {"1", "true", "yes", "on"}


@router.get("/stream")
async def stream_events(request: Request, heartbeat_ms: int = 15000, max_events: int | None = None):
    if not _sse_enabled():
        raise HTTPException(status_code=503, detail="SSE stream is disabled")

    interval = max(0.2, min(heartbeat_ms / 1000.0, 60.0))
    event_bus.bind_loop(asyncio.get_running_loop())

    async def generate():
        queue = event_bus.subscribe()
        sent = 0
        elapsed = 0.0
        try:
            yield format_sse(build_event("heartbeat", "connected"))
            sent += 1
            if max_events is not None and sent >= max_events:
                return
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=min(interval, _DISCONNECT_POLL))
                    if event.get("event_type") == "_shutdown":
                        return
                    yield format_sse(event)
                    elapsed = 0.0
                except asyncio.TimeoutError:
                    elapsed += min(interval, _DISCONNECT_POLL)
                    if elapsed < interval:
                        continue
                    yield format_sse(build_event("heartbeat", "ping"))
                    elapsed = 0.0
                sent += 1
                if max_events is not None and sent >= max_events:
                    return
        except asyncio.CancelledError:
            raise
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
