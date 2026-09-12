from app.providers.gdacs import DisasterEventProvider, MockDisasterEventProvider
from app.providers.imd import MockWeatherProvider, WeatherProvider
from app.providers.mosdac import MockSatelliteProvider, SatelliteProvider
from app.providers.registry import (
    data_sources_for_snapshot,
    get_disaster_provider,
    get_satellite_provider,
    get_weather_provider,
    provider_status,
)

weather_provider = MockWeatherProvider()
disaster_provider = MockDisasterEventProvider()
satellite_provider = MockSatelliteProvider()

__all__ = [
    "WeatherProvider",
    "DisasterEventProvider",
    "SatelliteProvider",
    "weather_provider",
    "disaster_provider",
    "satellite_provider",
    "get_weather_provider",
    "get_disaster_provider",
    "get_satellite_provider",
    "provider_status",
    "data_sources_for_snapshot",
]
