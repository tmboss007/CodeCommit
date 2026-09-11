from typing import Dict, List, Optional, Tuple
from app.services.priority import calculate_distance_km, estimate_eta_minutes


class RoutingProvider:
    mode = "UNAVAILABLE"

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        raise NotImplementedError


class SimulationRoutingProvider(RoutingProvider):
    mode = "SIMULATION"

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        if blocked:
            for item in blocked:
                if item.get("blocked") is True:
                    return 9999, "ROUTE_BLOCKED"
        dist = calculate_distance_km(lat1, lon1, lat2, lon2)
        return estimate_eta_minutes(dist, resource_type), "SIMULATION"


class LiveRoutingProvider(RoutingProvider):
    """Placeholder for OSRM/GraphHopper. Not used unless configured."""

    mode = "UNAVAILABLE"

    def eta_minutes(self, lat1, lon1, lat2, lon2, resource_type: str, blocked: Optional[List] = None) -> Tuple[int, str]:
        return SimulationRoutingProvider().eta_minutes(lat1, lon1, lat2, lon2, resource_type, blocked)


def get_routing_provider(name: str = "simulation") -> RoutingProvider:
    if name == "osrm":
        return LiveRoutingProvider()
    return SimulationRoutingProvider()
