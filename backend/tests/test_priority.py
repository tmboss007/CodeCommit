import pytest
from app.services.priority import PriorityCalculator, NeedsCalculator

def test_priority_calculation():
    """Test priority score calculation."""
    score, breakdown = PriorityCalculator.calculate_priority(
        severity=8.0,
        affected_population=2000,
        vulnerable_population=400,
        total_population=10000,
        resource_deficit_ratio=0.6,
        hours_since_incident=2.0
    )

    assert 0 <= score <= 100
    assert score > 70  # Should be high priority
    assert 'severity' in breakdown
    assert 'affected_population' in breakdown
    assert 'vulnerability' in breakdown
    assert 'resource_deficit' in breakdown
    assert 'time_criticality' in breakdown

def test_priority_weights_sum_to_one():
    """Verify priority weights sum to 1.0."""
    weights = PriorityCalculator.WEIGHTS
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01  # Allow small floating point error

def test_needs_calculation_flood():
    """Test needs calculation for flood incident."""
    needs = NeedsCalculator.calculate_needs(
        affected_population=1000,
        vulnerable_population=150,
        incident_type='flood',
        severity=7.0
    )

    assert len(needs) > 0

    # Check essential resources
    types = [n['type'] for n in needs]
    assert 'water_liter' in types
    assert 'food_packet' in types
    assert 'rescue_team' in types
    assert 'medical_kit' in types

    # Flood should prioritize rescue teams
    rescue = next(n for n in needs if n['type'] == 'rescue_team')
    assert rescue['quantity'] > 0
    assert rescue['urgency'] >= 0.9

def test_needs_scale_with_population():
    """Test needs scale proportionally with population."""
    needs_small = NeedsCalculator.calculate_needs(500, 75, 'flood', 5.0)
    needs_large = NeedsCalculator.calculate_needs(5000, 750, 'flood', 5.0)

    water_small = next(n for n in needs_small if n['type'] == 'water_liter')
    water_large = next(n for n in needs_large if n['type'] == 'water_liter')

    assert water_large['quantity'] > water_small['quantity']
    assert water_large['quantity'] / water_small['quantity'] > 5

def test_severity_affects_needs():
    """Test severity impacts calculated needs."""
    needs_low = NeedsCalculator.calculate_needs(1000, 150, 'flood', 3.0)
    needs_high = NeedsCalculator.calculate_needs(1000, 150, 'flood', 9.0)

    water_low = next(n for n in needs_low if n['type'] == 'water_liter')
    water_high = next(n for n in needs_high if n['type'] == 'water_liter')

    assert water_high['quantity'] > water_low['quantity']
