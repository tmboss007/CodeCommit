"""IMD weather. Live uses documented api.imd.gov.in v1 paths. Auth is portal-issued."""
from typing import Any, Dict, List, Optional

from app.providers.base import provenance, utc_now
from app.providers.http import http_get


class WeatherProvider:
    mode = "SIMULATION"

    def current(self, lat: float, lon: float) -> Dict[str, Any]:
        raise NotImplementedError

    def warnings(self, lat: float = 19.076, lon: float = 72.8777) -> List[Dict[str, Any]]:
        return []


class MockWeatherProvider(WeatherProvider):
    mode = "SIMULATION"

    def current(self, lat: float, lon: float) -> Dict[str, Any]:
        now = utc_now()
        return provenance(
            "IMD",
            "SIMULATION",
            event_time=now,
            fetched_at=now,
            confidence=0.5,
            extra={
                "kind": "WeatherObservation",
                "location": {"lat": lat, "lon": lon},
                "condition": "Heavy rain (simulated)",
                "rainfall_mm": 42,
                "station_id": None,
            },
        )

    def warnings(self, lat: float = 19.076, lon: float = 72.8777) -> List[Dict[str, Any]]:
        now = utc_now()
        return [
            provenance(
                "IMD",
                "SIMULATION",
                event_time=now,
                fetched_at=now,
                extra={
                    "kind": "WeatherWarning",
                    "headline": "Orange alert — coastal flooding risk",
                    "level": "Orange",
                    "location": {"lat": lat, "lon": lon},
                },
            )
        ]


class IMDProvider(WeatherProvider):
    """Documented endpoints from https://api.imd.gov.in/public/api_reference.html

    Current weather: GET /api/v1/current_wx
    District warnings: GET /api/v1/districtwarning

    Authentication is issued by the IMD API portal. This client sends X-API-Key.
    """

    mode = "LIVE"

    def __init__(self, base_url: str, api_key: str):
        if not api_key:
            raise ValueError("IMD_API_KEY is required for live IMD")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def current(self, lat: float, lon: float) -> Dict[str, Any]:
        response = http_get(f"{self.base_url}/current_wx", headers=self._headers())
        response.raise_for_status()
        return normalize_imd_observation(response.json(), lat, lon, utc_now())

    def warnings(self, lat: float = 19.076, lon: float = 72.8777) -> List[Dict[str, Any]]:
        response = http_get(f"{self.base_url}/districtwarning", headers=self._headers())
        response.raise_for_status()
        return normalize_imd_warnings(response.json(), lat, lon, utc_now())


def _first_record(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, list) and payload:
        row = payload[0]
        return row if isinstance(row, dict) else {"value": row}
    if isinstance(payload, dict):
        for key in ("data", "records", "result", "stations"):
            inner = payload.get(key)
            if isinstance(inner, list) and inner and isinstance(inner[0], dict):
                return inner[0]
            if isinstance(inner, dict):
                return inner
        return payload
    raise ValueError("IMD payload is not an object")


def normalize_imd_observation(payload: Any, lat: float, lon: float, fetched_at: str) -> Dict[str, Any]:
    row = _first_record(payload)
    rainfall = row.get("Past24hrRainfall") or row.get("rainfall_mm") or row.get("Last 24 hrs Rainfall") or row.get("rf")
    try:
        rainfall_mm = float(rainfall) if rainfall not in (None, "") else None
    except (TypeError, ValueError):
        rainfall_mm = None
    weather_code = row.get("Weather Code") or row.get("WeatherCode") or row.get("ww")
    event_time = row.get("Date of Observation") or row.get("Date") or row.get("obs_date") or row.get("time")
    if event_time is not None:
        event_time = str(event_time)
        time_part = row.get("Time of Observation") or row.get("Time")
        if time_part:
            event_time = f"{event_time}T{time_part}"
    condition = row.get("condition") or (f"Weather code {weather_code}" if weather_code is not None else "IMD observation")
    return provenance(
        "IMD",
        "LIVE",
        event_time=event_time,
        fetched_at=fetched_at,
        confidence=0.75,
        extra={
            "kind": "WeatherObservation",
            "location": {"lat": lat, "lon": lon, "station_id": row.get("id") or row.get("StationId")},
            "condition": condition,
            "rainfall_mm": rainfall_mm,
            "station_id": row.get("id") or row.get("StationId"),
        },
    )


def normalize_imd_warnings(payload: Any, lat: float, lon: float, fetched_at: str) -> List[Dict[str, Any]]:
    rows: List[Any]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data") or payload.get("warnings") or [payload]
    else:
        raise ValueError("IMD warning payload is invalid")
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        headline = item.get("warning") or item.get("headline") or item.get("message") or item.get("color")
        if not headline:
            continue
        event_time = item.get("date") or item.get("issue_time")
        out.append(
            provenance(
                "IMD",
                "LIVE",
                event_time=str(event_time) if event_time else None,
                fetched_at=fetched_at,
                extra={
                    "kind": "WeatherWarning",
                    "headline": str(headline),
                    "level": item.get("level") or item.get("color") or item.get("alert"),
                    "location": {"lat": lat, "lon": lon, "district": item.get("district") or item.get("id")},
                },
            )
        )
    if not out:
        raise ValueError("IMD warning payload contained no warnings")
    return out


class FallbackWeatherProvider(WeatherProvider):
    def __init__(self, live: Optional[WeatherProvider], mock: WeatherProvider, blocked: Optional[str] = None):
        self.live = live
        self.mock = mock
        self.mode = "SIMULATION"
        self.fallback_reason = blocked

    def current(self, lat: float, lon: float) -> Dict[str, Any]:
        if self.live is None:
            self.mode = "SIMULATION"
            row = self.mock.current(lat, lon)
            if self.fallback_reason:
                row["fallback_reason"] = self.fallback_reason
            return row
        try:
            row = self.live.current(lat, lon)
            self.mode = "LIVE"
            self.fallback_reason = None
            return row
        except Exception as exc:
            self.mode = "SIMULATION"
            self.fallback_reason = str(exc)
            row = self.mock.current(lat, lon)
            row["fallback_reason"] = self.fallback_reason
            return row

    def warnings(self, lat: float = 19.076, lon: float = 72.8777) -> List[Dict[str, Any]]:
        if self.live is None:
            return self.mock.warnings(lat, lon)
        try:
            return self.live.warnings(lat, lon)
        except Exception:
            return self.mock.warnings(lat, lon)
