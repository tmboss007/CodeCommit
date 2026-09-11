import pytest
from app.agents.replanning import ReplanningAgent

def test_priority_change_triggers_replan():
    """Test that significant priority changes trigger replanning."""
    agent = ReplanningAgent()

    old_state = {
        'zones': [
            {'id': 'Z1', 'priority_score': 60, 'severity': 5.0},
        ],
        'resources': []
    }

    new_state = {
        'zones': [
            {'id': 'Z1', 'priority_score': 85, 'severity': 8.0},  # +25 priority
        ],
        'resources': []
    }

    should_replan, reason, details = agent.should_replan(old_state, new_state, [])

    assert should_replan is True
    assert 'priority' in reason.lower()
    assert 'priority_changes' in details

def test_small_changes_dont_trigger_replan():
    """Test that minor changes don't trigger unnecessary replanning."""
    agent = ReplanningAgent()

    old_state = {
        'zones': [
            {'id': 'Z1', 'priority_score': 60, 'severity': 5.0},
        ],
        'resources': []
    }

    new_state = {
        'zones': [
            {'id': 'Z1', 'priority_score': 65, 'severity': 5.2},  # Small change
        ],
        'resources': []
    }

    should_replan, reason, details = agent.should_replan(old_state, new_state, [])

    assert should_replan is False

def test_resource_unavailability_triggers_replan():
    """Test that resource becoming unavailable triggers replanning."""
    agent = ReplanningAgent()

    old_state = {
        'zones': [],
        'resources': [
            {'id': 'R1', 'status': 'available'},
        ]
    }

    new_state = {
        'zones': [],
        'resources': [
            {'id': 'R1', 'status': 'unavailable'},
        ]
    }

    should_replan, reason, details = agent.should_replan(old_state, new_state, [])

    assert should_replan is True
    assert 'resource' in reason.lower()

def test_allocation_delta_calculation():
    """Test computation of allocation differences."""
    agent = ReplanningAgent()

    old_allocations = [
        {'id': 'A1', 'resource_id': 'R1', 'zone_id': 'Z1', 'quantity': 100},
        {'id': 'A2', 'resource_id': 'R2', 'zone_id': 'Z2', 'quantity': 50},
    ]

    new_allocations = [
        {'id': 'A1', 'resource_id': 'R1', 'zone_id': 'Z1', 'quantity': 150},  # Modified
        {'id': 'A3', 'resource_id': 'R3', 'zone_id': 'Z3', 'quantity': 75},   # Added
        # A2 removed
    ]

    delta = agent.compute_allocation_delta(old_allocations, new_allocations)

    assert len(delta['added']) == 1
    assert len(delta['removed']) == 1
    assert len(delta['modified']) == 1
    assert delta['added'][0]['resource_id'] == 'R3'
    assert delta['removed'][0]['resource_id'] == 'R2'
