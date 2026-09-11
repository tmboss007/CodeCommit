from datetime import datetime, timezone
from typing import Dict, List


class WeatherProvider:
    mode = "SIMULATION"

    def current(self, lat: float, lon: float) -> Dict:
        return {
            "provider": "IMD",
            "mode": self.mode,
            "location": {"lat": lat, "lon": lon},
            "condition": "Heavy rain (simulated)",
            "rainfall_mm": 42,
            "warning": "Orange alert — coastal flooding risk",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


class DisasterEventProvider:
    mode = "SIMULATION"

    def events(self) -> List[Dict]:
        return [
            {
                "provider": "GDACS",
                "mode": self.mode,
                "event_type": "flood",
                "severity": "Orange",
                "title": "Simulated flood event — Mumbai coastal belt",
                "observed_at": datetime.now(timezone.utc).isoformat(),
            }
        ]


class SatelliteProvider:
    mode = "SIMULATION"

    def snapshot(self, zone_id: str) -> Dict:
        return {
            "provider": "MOSDAC",
            "mode": self.mode,
            "zone_id": zone_id,
            "inundation_indicator": "elevated",
            "cloud_cover_pct": 78,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


weather_provider = WeatherProvider()
disaster_provider = DisasterEventProvider()
satellite_provider = SatelliteProvider()
