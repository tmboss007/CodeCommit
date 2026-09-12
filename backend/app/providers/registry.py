from typing import Any, Dict, List

from app.core.config import settings
from app.providers.base import want_live
from app.providers.gdacs import FallbackDisasterProvider, GDACSProvider, MockDisasterEventProvider
from app.providers.imd import FallbackWeatherProvider, IMDProvider, MockWeatherProvider
from app.providers.mosdac import FallbackSatelliteProvider, MockSatelliteProvider, MOSDACProvider
from app.services.routing import get_routing_provider


def _status(name: str, label: str, mode: str, *, fallback_reason=None, extra=None) -> Dict[str, Any]:
    row = {"id": name, "label": label, "mode": mode}
    if fallback_reason:
        row["fallback"] = True
        row["reason"] = fallback_reason
    if extra:
        row.update(extra)
    return row


def get_weather_provider() -> FallbackWeatherProvider:
    mock = MockWeatherProvider()
    if not want_live(settings.IMD_MODE, settings.DATA_MODE):
        return FallbackWeatherProvider(None, mock)
    if not settings.IMD_API_KEY:
        return FallbackWeatherProvider(
            None,
            mock,
            blocked="IMD_API_KEY required (register at https://api.imd.gov.in/public/index.php)",
        )
    return FallbackWeatherProvider(IMDProvider(settings.IMD_API_BASE, settings.IMD_API_KEY), mock)


def get_disaster_provider():
    mock = MockDisasterEventProvider()
    if not want_live(settings.GDACS_MODE, settings.DATA_MODE):
        return mock
    return FallbackDisasterProvider(GDACSProvider(settings.GDACS_API_URL), mock)


def get_satellite_provider() -> FallbackSatelliteProvider:
    mock = MockSatelliteProvider()
    blocked = "MOSDAC dataset access is account-gated; adapter is ready, default is simulation"
    if not want_live(settings.MOSDAC_MODE, settings.DATA_MODE):
        return FallbackSatelliteProvider(None, mock, blocked=blocked)
    try:
        live = MOSDACProvider(settings.MOSDAC_API_URL, settings.MOSDAC_API_KEY)
    except ValueError as exc:
        return FallbackSatelliteProvider(None, mock, blocked=str(exc))
    return FallbackSatelliteProvider(live, mock)


def data_sources_for_snapshot() -> List[Dict[str, Any]]:
    """Configured labels only — do not HTTP-probe on every ops snapshot."""
    routing = get_routing_provider()
    mosdac_blocked = None
    if not want_live(settings.MOSDAC_MODE, settings.DATA_MODE):
        mosdac_blocked = "MOSDAC dataset access is account-gated; adapter is ready, default is simulation"
    elif not settings.MOSDAC_API_URL or not settings.MOSDAC_API_KEY:
        mosdac_blocked = "MOSDAC_API_URL and MOSDAC_API_KEY are required for live MOSDAC"
    imd_reason = None
    if want_live(settings.IMD_MODE, settings.DATA_MODE) and not settings.IMD_API_KEY:
        imd_reason = "IMD_API_KEY required (register at https://api.imd.gov.in/public/index.php)"
    return [
        _status("gdacs", "GDACS", "LIVE" if want_live(settings.GDACS_MODE, settings.DATA_MODE) else "SIMULATION"),
        _status("imd", "IMD", "LIVE" if want_live(settings.IMD_MODE, settings.DATA_MODE) and settings.IMD_API_KEY else "SIMULATION", fallback_reason=imd_reason),
        _status(
            "mosdac",
            "MOSDAC",
            "LIVE" if want_live(settings.MOSDAC_MODE, settings.DATA_MODE) and settings.MOSDAC_API_URL and settings.MOSDAC_API_KEY else "SIMULATION",
            fallback_reason=mosdac_blocked,
            extra={"adapter": "ADAPTER READY"},
        ),
        _status("routing", "Routing", routing.mode),
    ]


def provider_status() -> Dict[str, Any]:
    weather = get_weather_provider()
    disaster = get_disaster_provider()
    satellite = get_satellite_provider()
    routing = get_routing_provider()
    weather.current(19.076, 72.8777)
    disaster.fetch_events()
    satellite.snapshot("ZONE_A")
    return {
        "data_mode": (settings.DATA_MODE or "simulation").upper(),
        "sources": [
            _status("gdacs", "GDACS", getattr(disaster, "mode", "SIMULATION"), fallback_reason=getattr(disaster, "fallback_reason", None)),
            _status("imd", "IMD", weather.mode, fallback_reason=getattr(weather, "fallback_reason", None)),
            _status(
                "mosdac",
                "MOSDAC",
                satellite.mode,
                fallback_reason=getattr(satellite, "fallback_reason", None),
                extra={"adapter": getattr(satellite, "status", satellite.mode)},
            ),
            _status("routing", "Routing", routing.mode),
        ],
    }
