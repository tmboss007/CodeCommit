import pytest
from app.services.optimizer import ResourceOptimizer

def test_optimizer_basic_allocation():
    """Test basic resource allocation."""
    optimizer = ResourceOptimizer()

    zones = [
        {'id': 'Z1', 'name': 'Zone 1', 'priority_score': 80, 'latitude': 19.0, 'longitude': 72.8},
        {'id': 'Z2', 'name': 'Zone 2', 'priority_score': 60, 'latitude': 19.1, 'longitude': 72.9},
    ]

    resources = [
        {'id': 'R1', 'name': 'Team 1', 'type': 'rescue_team', 'quantity': 1, 'status': 'available', 'latitude': 19.0, 'longitude': 72.8},
        {'id': 'R2', 'name': 'Water 1', 'type': 'water_liter', 'quantity': 5000, 'status': 'available', 'latitude': 19.1, 'longitude': 72.9},
    ]

    needs = {
        'Z1': {'rescue_team': 1, 'water_liter': 2000},
        'Z2': {'rescue_team': 1, 'water_liter': 3000},
    }

    distances = {
        ('R1', 'Z1'): 5.0,
        ('R1', 'Z2'): 15.0,
        ('R2', 'Z1'): 12.0,
        ('R2', 'Z2'): 6.0,
    }

    allocations, unmet, explanation = optimizer.optimize_allocation(zones, resources, needs, distances)

    assert len(allocations) > 0
    assert isinstance(unmet, list)
    assert explanation != ""

    # High priority zone should get resources
    z1_allocations = [a for a in allocations if a['zone_id'] == 'Z1']
    assert len(z1_allocations) > 0

def test_resource_capacity_constraint():
    """Test that resources aren't over-allocated."""
    optimizer = ResourceOptimizer()

    zones = [
        {'id': 'Z1', 'name': 'Zone 1', 'priority_score': 80, 'latitude': 19.0, 'longitude': 72.8},
        {'id': 'Z2', 'name': 'Zone 2', 'priority_score': 75, 'latitude': 19.1, 'longitude': 72.9},
    ]

    resources = [
        {'id': 'R1', 'name': 'Water Supply', 'type': 'water_liter', 'quantity': 1000, 'status': 'available', 'latitude': 19.0, 'longitude': 72.8},
    ]

    needs = {
        'Z1': {'water_liter': 2000},
        'Z2': {'water_liter': 3000},
    }

    distances = {
        ('R1', 'Z1'): 5.0,
        ('R1', 'Z2'): 8.0,
    }

    allocations, unmet, _ = optimizer.optimize_allocation(zones, resources, needs, distances)

    # Total allocated should not exceed resource capacity
    total_allocated = sum(a['quantity'] for a in allocations if a['resource_id'] == 'R1')
    assert total_allocated <= 1000

    # Should have unmet demand
    assert len(unmet) > 0

def test_unavailable_resources_not_allocated():
    """Test that unavailable resources are not allocated."""
    optimizer = ResourceOptimizer()

    zones = [{'id': 'Z1', 'name': 'Zone 1', 'priority_score': 80, 'latitude': 19.0, 'longitude': 72.8}]

    resources = [
        {'id': 'R1', 'name': 'Team 1', 'type': 'rescue_team', 'quantity': 1, 'status': 'unavailable', 'latitude': 19.0, 'longitude': 72.8},
    ]

    needs = {'Z1': {'rescue_team': 1}}
    distances = {('R1', 'Z1'): 5.0}

    allocations, unmet, _ = optimizer.optimize_allocation(zones, resources, needs, distances)

    # No allocations should be made from unavailable resource
    assert len(allocations) == 0
    assert len(unmet) > 0
