"""GDACS disaster events. Live uses official Events/geteventlist/latest."""
from typing import Any, Dict, List, Optional

from app.providers.base import provenance, utc_now
from app.providers.http import http_get

EVENT_TYPES = {
    "FL": "flood",
    "EQ": "earthquake",
    "TC": "cyclone",
    "VO": "volcanic",
    "DR": "drought",
    "WF": "wildfire",
    "TS": "tsunami",
}


class DisasterEventProvider:
    mode = "SIMULATION"

    def fetch_events(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class MockDisasterEventProvider(DisasterEventProvider):
    mode = "SIMULATION"

    def fetch_events(self) -> List[Dict[str, Any]]:
        now = utc_now()
        return [
            provenance(
                "GDACS",
                "SIMULATION",
                event_time=now,
                fetched_at=now,
                confidence=0.55,
                extra={
                    "event_type": "flood",
                    "alert_level": "Orange",
                    "title": "Simulated flood event — Mumbai coastal belt",
                    "location": {"lat": 19.076, "lon": 72.8777, "country": "India"},
                    "geometry": {"type": "Point", "coordinates": [72.8777, 19.076]},
                    "external_id": "sim-gdacs-mumbai-flood",
                },
            )
        ]

    def events(self) -> List[Dict[str, Any]]:
        return self.fetch_events()


class GDACSProvider(DisasterEventProvider):
    mode = "LIVE"

    def __init__(self, url: str):
        self.url = url

    def fetch_events(self) -> List[Dict[str, Any]]:
        response = http_get(
            self.url,
            params={"eventlist": "EQ,TC,FL,VO,DR,WF", "pageSize": 20},
        )
        response.raise_for_status()
        payload = response.json()
        features = _features(payload)
        if not isinstance(features, list):
            raise ValueError("GDACS payload has no feature list")
        fetched = utc_now()
        out = [normalize_gdacs_feature(item, fetched) for item in features]
        out = [row for row in out if row]
        if not out:
            raise ValueError("GDACS payload contained no usable events")
        return out


def _features(payload: Any) -> List:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("GDACS payload is not an object")
    for key in ("features", "Features", "events", "Events"):
        if isinstance(payload.get(key), list):
            return payload[key]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("features"), list):
        return data["features"]
    if isinstance(data, list):
        return data
    raise ValueError("GDACS payload has no feature list")


def normalize_gdacs_feature(item: Dict[str, Any], fetched_at: str) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    props = item.get("properties") if isinstance(item.get("properties"), dict) else item
    geom = item.get("geometry") if isinstance(item.get("geometry"), dict) else None
    coords = (geom or {}).get("coordinates") if geom else props.get("coordinates")
    lon = lat = None
    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
        lon, lat = float(coords[0]), float(coords[1])
    raw_type = str(props.get("eventtype") or props.get("event_type") or props.get("type") or "")
    event_type = EVENT_TYPES.get(raw_type.upper(), raw_type.lower() or "other")
    event_time = props.get("fromdate") or props.get("todate") or props.get("date") or props.get("datemodified")
    if event_time is not None:
        event_time = str(event_time)
    title = props.get("eventname") or props.get("name") or props.get("title") or f"GDACS {event_type}"
    external_id = str(props.get("eventid") or props.get("episodeid") or props.get("id") or title)
    alert = props.get("alertlevel") or props.get("alert_level") or props.get("alert") or "Green"
    return provenance(
        "GDACS",
        "LIVE",
        event_time=event_time,
        fetched_at=fetched_at,
        confidence=0.8,
        extra={
            "event_type": event_type,
            "alert_level": alert,
            "title": title,
            "location": {
                "lat": lat,
                "lon": lon,
                "country": props.get("country") or props.get("iso3"),
            },
            "geometry": geom,
            "external_id": external_id,
        },
    )


class FallbackDisasterProvider(DisasterEventProvider):
    def __init__(self, live: DisasterEventProvider, mock: DisasterEventProvider):
        self.live = live
        self.mock = mock
        self.mode = "SIMULATION"
        self.fallback_reason = None

    def fetch_events(self) -> List[Dict[str, Any]]:
        try:
            rows = self.live.fetch_events()
            self.mode = "LIVE"
            self.fallback_reason = None
            return rows
        except Exception as exc:
            self.mode = "SIMULATION"
            self.fallback_reason = str(exc)
            rows = self.mock.fetch_events()
            for row in rows:
                row["fallback_reason"] = self.fallback_reason
            return rows

    def events(self) -> List[Dict[str, Any]]:
        return self.fetch_events()
