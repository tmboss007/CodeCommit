import math
from typing import Dict, List, Tuple
from geopy.distance import geodesic

class PriorityCalculator:
    """Calculate priority scores for zones based on multiple factors."""

    WEIGHTS = {
        "severity": 0.30,
        "affected_population": 0.25,
        "vulnerability": 0.20,
        "resource_deficit": 0.15,
        "time_criticality": 0.10
    }

    @staticmethod
    def calculate_priority(
        severity: float,
        affected_population: int,
        vulnerable_population: int,
        total_population: int,
        resource_deficit_ratio: float,
        hours_since_incident: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate priority score (0-100) with factor breakdown.

        Returns: (priority_score, factor_breakdown)
        """
        # Severity score (already 0-10, normalize to 0-100)
        severity_score = severity * 10

        # Affected population score
        pop_ratio = affected_population / max(total_population, 1)
        affected_pop_score = min(pop_ratio * 100, 100)

        # Vulnerability score
        vuln_ratio = vulnerable_population / max(affected_population, 1)
        vulnerability_score = vuln_ratio * 100

        # Resource deficit score (0-1 input, scale to 0-100)
        deficit_score = resource_deficit_ratio * 100

        # Time criticality (exponential decay for urgency)
        # Peak urgency in first 6 hours, then decreases
        time_score = 100 * math.exp(-hours_since_incident / 12)

        # Weighted sum
        priority = (
            PriorityCalculator.WEIGHTS["severity"] * severity_score +
            PriorityCalculator.WEIGHTS["affected_population"] * affected_pop_score +
            PriorityCalculator.WEIGHTS["vulnerability"] * vulnerability_score +
            PriorityCalculator.WEIGHTS["resource_deficit"] * deficit_score +
            PriorityCalculator.WEIGHTS["time_criticality"] * time_score
        )

        breakdown = {
            "severity": round(severity_score, 2),
            "affected_population": round(affected_pop_score, 2),
            "vulnerability": round(vulnerability_score, 2),
            "resource_deficit": round(deficit_score, 2),
            "time_criticality": round(time_score, 2),
            "priority": round(priority, 2)
        }

        return round(priority, 2), breakdown

class NeedsCalculator:
    """Calculate resource needs based on affected population and incident type."""

    # Configurable rules per person per day
    NEEDS_PER_PERSON = {
        "water_liter": 3.0,
        "food_packet": 2.0,
        "medical_kit_per_100": 0.5,
        "rescue_team_per_1000": 1.0,
        "shelter_capacity": 1.0
    }

    INCIDENT_TYPE_MULTIPLIERS = {
        "flood": {"rescue_team": 2.0, "water": 1.5, "medical": 1.2},
        "earthquake": {"rescue_team": 2.5, "medical": 2.0, "shelter": 1.5},
        "cyclone": {"shelter": 2.0, "water": 1.3, "food": 1.2},
        "fire": {"rescue_team": 1.8, "medical": 1.5},
        "landslide": {"rescue_team": 2.2, "medical": 1.3}
    }

    @classmethod
    def calculate_needs(
        cls,
        affected_population: int,
        vulnerable_population: int,
        incident_type: str,
        severity: float
    ) -> List[Dict]:
        """Calculate resource requirements."""
        needs = []
        multipliers = cls.INCIDENT_TYPE_MULTIPLIERS.get(incident_type, {})
        severity_factor = severity / 10.0  # Normalize 0-10 to 0-1

        # Water
        water_base = affected_population * cls.NEEDS_PER_PERSON["water_liter"]
        water_multiplier = multipliers.get("water", 1.0)
        needs.append({
            "type": "water_liter",
            "quantity": int(water_base * water_multiplier * (0.5 + severity_factor)),
            "unit": "liters",
            "urgency": 0.9
        })

        # Food
        food_base = affected_population * cls.NEEDS_PER_PERSON["food_packet"]
        food_multiplier = multipliers.get("food", 1.0)
        needs.append({
            "type": "food_packet",
            "quantity": int(food_base * food_multiplier * (0.5 + severity_factor)),
            "unit": "packets",
            "urgency": 0.7
        })

        # Medical kits
        medical_base = (affected_population / 100) * cls.NEEDS_PER_PERSON["medical_kit_per_100"]
        medical_multiplier = multipliers.get("medical", 1.0)
        needs.append({
            "type": "medical_kit",
            "quantity": int(medical_base * medical_multiplier * severity_factor) + 5,
            "unit": "kits",
            "urgency": 0.85
        })

        # Rescue teams
        rescue_base = (affected_population / 1000) * cls.NEEDS_PER_PERSON["rescue_team_per_1000"]
        rescue_multiplier = multipliers.get("rescue_team", 1.0)
        needs.append({
            "type": "rescue_team",
            "quantity": max(1, int(rescue_base * rescue_multiplier * severity_factor)),
            "unit": "teams",
            "urgency": 0.95
        })

        # Shelter (if high severity or specific incident types)
        if severity >= 6 or incident_type in ["cyclone", "earthquake", "flood"]:
            shelter_base = affected_population * cls.NEEDS_PER_PERSON["shelter_capacity"]
            shelter_multiplier = multipliers.get("shelter", 1.0)
            needs.append({
                "type": "shelter_capacity",
                "quantity": int(shelter_base * shelter_multiplier * 0.6),
                "unit": "persons",
                "urgency": 0.8
            })

        return needs

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two points."""
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def estimate_eta_minutes(distance_km: float, resource_type: str) -> int:
    """Estimate travel time based on distance and resource type."""
    # Average speeds (km/h) by resource type
    speeds = {
        "rescue_team": 60,
        "medical_team": 70,
        "fire_team": 65,
        "default": 50
    }

    speed = speeds.get(resource_type, speeds["default"])
    hours = distance_km / speed
    return int(hours * 60) + 10  # Add 10 min buffer
