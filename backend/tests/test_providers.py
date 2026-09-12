from unittest.mock import patch

from app.core.database import SessionLocal, engine, Base
from app.providers.base import want_live
from app.providers.gdacs import MockDisasterEventProvider, normalize_gdacs_feature
from app.providers.imd import MockWeatherProvider, normalize_imd_observation, normalize_imd_warnings
from app.providers.mosdac import MockSatelliteProvider
from app.providers.registry import get_disaster_provider, get_weather_provider, provider_status
from app.services.orchestration import OrchestrationService
from app.services.routing import LiveRoutingProvider, SimulationRoutingProvider


GDACS_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [72.88, 19.08]},
    "properties": {
        "eventtype": "FL",
        "eventid": 1001,
        "eventname": "India flood",
        "fromdate": "2026-09-01T00:00:00",
        "alertlevel": "Orange",
        "country": "India",
    },
}


def test_gdacs_normalization_keeps_event_and_fetch_times():
    fetched = "2026-09-11T12:00:00+00:00"
    row = normalize_gdacs_feature(GDACS_FEATURE, fetched)
    assert row["source"] == "GDACS"
    assert row["data_mode"] == "LIVE"
    assert row["event_type"] == "flood"
    assert row["alert_level"] == "Orange"
    assert row["event_time"] == "2026-09-01T00:00:00"
    assert row["fetched_at"] == fetched
    assert row["event_time"] != row["fetched_at"]
    assert row["location"]["lat"] == 19.08


def test_gdacs_failure_fallback():
    with patch("app.providers.gdacs.http_get", side_effect=Exception("timeout")):
        from app.providers.gdacs import FallbackDisasterProvider, GDACSProvider

        provider = FallbackDisasterProvider(GDACSProvider("http://example.invalid"), MockDisasterEventProvider())
        rows = provider.fetch_events()
        assert provider.mode == "SIMULATION"
        assert rows[0]["data_mode"] == "SIMULATION"
        assert rows[0]["source"] == "GDACS"
        assert "timeout" in rows[0]["fallback_reason"]


def test_imd_normalization():
    fetched = "2026-09-11T12:00:00+00:00"
    obs = normalize_imd_observation(
        {"Date of Observation": "2026-09-10", "Time of Observation": "03:00", "Weather Code": 21, "Past24hrRainfall": 12},
        19.07,
        72.87,
        fetched,
    )
    assert obs["source"] == "IMD"
    assert obs["kind"] == "WeatherObservation"
    assert obs["rainfall_mm"] == 12
    assert obs["event_time"].startswith("2026-09-10")
    assert obs["fetched_at"] == fetched
    warnings = normalize_imd_warnings([{"warning": "Orange alert", "district": "Mumbai", "date": "2026-09-10"}], 19.07, 72.87, fetched)
    assert warnings[0]["kind"] == "WeatherWarning"
    assert warnings[0]["source"] == "IMD"


def test_imd_failure_fallback():
    with patch("app.providers.imd.http_get", side_effect=Exception("401")):
        from app.providers.imd import FallbackWeatherProvider, IMDProvider

        provider = FallbackWeatherProvider(IMDProvider("http://example.invalid", "k"), MockWeatherProvider())
        row = provider.current(19.0, 72.0)
        assert provider.mode == "SIMULATION"
        assert row["data_mode"] == "SIMULATION"
        assert row["source"] == "IMD"


def test_mosdac_adapter_simulation():
    row = MockSatelliteProvider().snapshot("ZONE_A")
    assert row["source"] == "MOSDAC"
    assert row["data_mode"] == "SIMULATION"
    assert row["zone_id"] == "ZONE_A"
    assert row["fetched_at"]
    assert row["event_time"]


def test_routing_failure_fallback():
    provider = LiveRoutingProvider("http://example.invalid")
    with patch("app.services.routing.http_get", side_effect=Exception("osrm down")):
        row = provider.route(19.07, 72.87, 19.11, 72.86)
        assert row["data_mode"] == "SIMULATION"
        assert row["status"] == "SIMULATION"
        assert "osrm down" in row["fallback_reason"]
        eta, status = provider.eta_minutes(19.07, 72.87, 19.11, 72.86, "rescue_team")
        assert status == "SIMULATION"
        assert eta >= 10


def test_data_mode_labeling_default_simulation():
    assert want_live(None, "simulation") is False
    status = provider_status()
    modes = {s["id"]: s["mode"] for s in status["sources"]}
    assert modes["gdacs"] == "SIMULATION"
    assert modes["imd"] == "SIMULATION"
    assert modes["mosdac"] == "SIMULATION"
    assert modes["routing"] == "SIMULATION"
    assert get_weather_provider().current(19.0, 72.0)["source"] == "IMD"


def test_source_attribution_on_mock_feeds():
    disaster = get_disaster_provider().fetch_events()[0]
    weather = get_weather_provider().current(19.07, 72.87)
    assert disaster["source"] == "GDACS"
    assert weather["source"] == "IMD"
    sim = SimulationRoutingProvider().route(19.0, 72.8, 19.1, 72.9)
    assert sim["source"] == "ROUTING"


def test_event_time_not_confused_with_fetched_at():
    row = normalize_gdacs_feature(GDACS_FEATURE, "2026-09-11T18:00:00+00:00")
    assert row["event_time"] == "2026-09-01T00:00:00"
    assert row["fetched_at"] == "2026-09-11T18:00:00+00:00"


def test_external_event_enters_operational_state():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        event = MockDisasterEventProvider().fetch_events()[0]
        result = orch.ingest_external_event(event, auto_replan=False)
        assert result["incident_id"]
        assert result["zone_id"] == "ZONE_A"
        assert result["provider_event"]["source"] == "GDACS"
        assert result["provider_event"]["event_time"]
        assert result["provider_event"]["fetched_at"]
        from app.models import Incident
        incident = db.query(Incident).filter(Incident.id == result["incident_id"]).first()
        assert incident.source == "GDACS"
        assert incident.report_text.startswith("GDACS")
    finally:
        db.close()
