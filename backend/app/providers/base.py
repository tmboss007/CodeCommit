from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def provenance(
    source: str,
    data_mode: str,
    *,
    event_time: Optional[str] = None,
    fetched_at: Optional[str] = None,
    confidence: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "source": source,
        "data_mode": data_mode,
        "fetched_at": fetched_at or utc_now(),
        "event_time": event_time,
    }
    if confidence is not None:
        row["confidence"] = confidence
    if extra:
        row.update(extra)
    return row


def want_live(override: Optional[str], data_mode: str) -> bool:
    raw = (override or data_mode or "simulation").strip().lower()
    return raw in {"live", "true", "1", "on"}
