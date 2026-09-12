"""MOSDAC satellite. Live requires portal account and dataset URL; otherwise simulation."""
from typing import Any, Dict, Optional

from app.providers.base import provenance, utc_now
from app.providers.http import http_get


class SatelliteProvider:
    mode = "SIMULATION"
    status = "SIMULATION"

    def snapshot(self, zone_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class MockSatelliteProvider(SatelliteProvider):
    mode = "SIMULATION"
    status = "SIMULATION"

    def snapshot(self, zone_id: str) -> Dict[str, Any]:
        now = utc_now()
        return provenance(
            "MOSDAC",
            "SIMULATION",
            event_time=now,
            fetched_at=now,
            confidence=0.45,
            extra={
                "zone_id": zone_id,
                "inundation_indicator": "elevated",
                "cloud_cover_pct": 78,
            },
        )


class MOSDACProvider(SatelliteProvider):
    mode = "LIVE"
    status = "ADAPTER READY"

    def __init__(self, url: Optional[str], api_key: Optional[str]):
        if not url or not api_key:
            raise ValueError("MOSDAC_API_URL and MOSDAC_API_KEY are required for live MOSDAC")
        self.url = url
        self.api_key = api_key

    def snapshot(self, zone_id: str) -> Dict[str, Any]:
        response = http_get(self.url, headers={"X-API-Key": self.api_key}, params={"zone_id": zone_id})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("MOSDAC payload is not an object")
        fetched = utc_now()
        event_time = payload.get("observation_time") or payload.get("event_time")
        return provenance(
            "MOSDAC",
            "LIVE",
            event_time=str(event_time) if event_time else None,
            fetched_at=fetched,
            confidence=0.7,
            extra={
                "zone_id": zone_id,
                "inundation_indicator": payload.get("inundation_indicator") or payload.get("inundation") or "unknown",
                "cloud_cover_pct": payload.get("cloud_cover_pct") or payload.get("cloud_cover"),
            },
        )


class FallbackSatelliteProvider(SatelliteProvider):
    def __init__(self, live: Optional[SatelliteProvider], mock: SatelliteProvider, blocked: Optional[str] = None):
        self.live = live
        self.mock = mock
        self.mode = "SIMULATION"
        self.status = "ADAPTER READY" if blocked else "SIMULATION"
        self.fallback_reason = blocked

    def snapshot(self, zone_id: str) -> Dict[str, Any]:
        if self.live is None:
            row = self.mock.snapshot(zone_id)
            if self.fallback_reason:
                row["fallback_reason"] = self.fallback_reason
            return row
        try:
            row = self.live.snapshot(zone_id)
            self.mode = "LIVE"
            self.status = "LIVE"
            self.fallback_reason = None
            return row
        except Exception as exc:
            self.mode = "SIMULATION"
            self.status = "ADAPTER READY"
            self.fallback_reason = str(exc)
            row = self.mock.snapshot(zone_id)
            row["fallback_reason"] = self.fallback_reason
            return row
