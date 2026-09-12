from typing import Dict, List, Optional, Tuple
from app.core.config import settings
from app.providers.base import provenance, utc_now, want_live
from app.providers.http import http_get
from app.services.priority import calculate_distance_km, estimate_eta_minutes


class RoutingProvider:
    mode = "UNAVAILABLE"

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        raise NotImplementedError

    def route(self, lat1, lon1, lat2, lon2, resource_type: str = "vehicle", blocked: Optional[List] = None) -> Dict:
        raise NotImplementedError


class SimulationRoutingProvider(RoutingProvider):
    mode = "SIMULATION"

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        result = self.route(lat1, lon1, lat2, lon2, resource_type, blocked)
        return int(result["duration"]), result["status"]

    def route(self, lat1, lon1, lat2, lon2, resource_type: str = "vehicle", blocked: Optional[List] = None) -> Dict:
        now = utc_now()
        if blocked:
            for item in blocked:
                if item.get("blocked") is True:
                    return provenance(
                        "ROUTING",
                        "SIMULATION",
                        event_time=now,
                        fetched_at=now,
                        extra={"distance": None, "duration": 9999, "route_geometry": None, "status": "ROUTE_BLOCKED"},
                    )
        dist = calculate_distance_km(lat1, lon1, lat2, lon2)
        duration = estimate_eta_minutes(dist, resource_type)
        return provenance(
            "ROUTING",
            "SIMULATION",
            event_time=now,
            fetched_at=now,
            extra={"distance": dist, "duration": duration, "route_geometry": None, "status": "SIMULATION"},
        )


class LiveRoutingProvider(RoutingProvider):
    """OSRM-compatible live routing. Used only when OSRM_BASE_URL is set."""

    mode = "LIVE"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.fallback = SimulationRoutingProvider()

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        result = self.route(lat1, lon1, lat2, lon2, resource_type, blocked)
        return int(result["duration"] or 0), result["status"]

    def route(self, lat1, lon1, lat2, lon2, resource_type: str = "vehicle", blocked: Optional[List] = None) -> Dict:
        if blocked:
            for item in blocked:
                if item.get("blocked") is True:
                    return self.fallback.route(lat1, lon1, lat2, lon2, resource_type, blocked)
        try:
            url = f"{self.base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
            response = http_get(url, params={"overview": "false"})
            response.raise_for_status()
            payload = response.json()
            routes = payload.get("routes") or []
            if not routes:
                raise ValueError("OSRM returned no routes")
            primary = routes[0]
            now = utc_now()
            distance_km = float(primary.get("distance") or 0) / 1000.0
            duration_min = int(round(float(primary.get("duration") or 0) / 60.0)) or 1
            row = provenance(
                "ROUTING",
                "LIVE",
                event_time=now,
                fetched_at=now,
                extra={
                    "distance": distance_km,
                    "duration": duration_min,
                    "route_geometry": primary.get("geometry"),
                    "status": "LIVE",
                },
            )
            self.mode = "LIVE"
            return row
        except Exception as exc:
            self.mode = "SIMULATION"
            row = self.fallback.route(lat1, lon1, lat2, lon2, resource_type, blocked)
            row["fallback_reason"] = str(exc)
            return row


def get_routing_provider(name: Optional[str] = None) -> RoutingProvider:
    live = want_live(settings.ROUTING_MODE, settings.DATA_MODE) or (name or settings.ROUTING_PROVIDER) == "osrm"
    if live and settings.OSRM_BASE_URL:
        return LiveRoutingProvider(settings.OSRM_BASE_URL)
    return SimulationRoutingProvider()
