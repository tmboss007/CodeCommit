from app.services.situation_heuristic import analyze_report_heuristic, duplicate_status_heuristic


def test_urgent_zone_a_extraction():
    text = (
        "Zone A water level has risen rapidly. Approximately 2,000 additional people affected. "
        "Two rescue routes are becoming inaccessible. Immediate evacuation support required."
    )
    result = analyze_report_heuristic(text, None)
    assert result["zone_id"] == "ZONE_A"
    assert result["incident_type"] == "flood"
    assert result["affected_population"] == 2000
    assert result["severity"] >= 9


def test_possible_duplicate_same_zone():
    existing = [{
        "id": "inc_1",
        "zone_id": "ZONE_A",
        "incident_type": "flood",
        "timestamp": None,
        "report_text": "Zone A coastal flooding. water supply disrupted.",
    }]
    result = duplicate_status_heuristic("Zone A flooding water", existing, "ZONE_A", "flood")
    assert result["duplicate_status"] in ("POSSIBLE_DUPLICATE", "CONFIRMED_DUPLICATE")
