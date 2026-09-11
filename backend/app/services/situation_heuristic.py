import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

ZONE_PATTERNS = [
    (r"zone\s*a\b", "ZONE_A"),
    (r"zone\s*b\b", "ZONE_B"),
    (r"zone\s*c\b", "ZONE_C"),
    (r"zone\s*d\b", "ZONE_D"),
    (r"zone\s*e\b", "ZONE_E"),
    (r"coastal", "ZONE_A"),
    (r"urban\s+center", "ZONE_B"),
    (r"rural", "ZONE_C"),
    (r"mountain", "ZONE_D"),
    (r"river", "ZONE_E"),
]

TYPE_KEYWORDS = {
    "flood": ["flood", "water level", "inundat", "submerged", "levee", "waterlogging", "drinking water", "shelter and water"],
    "earthquake": ["earthquake", "tremor", "seismic", "collapsed building"],
    "cyclone": ["cyclone", "hurricane", "storm surge", "typhoon"],
    "fire": ["fire", "blaze", "wildfire", "burn"],
    "landslide": ["landslide", "mudslide", "slope failure"],
}

SEVERITY_KEYWORDS = [
    (9.5, ["catastrophic", "immediate evacuation", "inaccessible", "trapped"]),
    (9.0, ["urgent", "critical", "rapidly", "immediate"]),
    (8.0, ["severe", "major", "widespread"]),
    (6.5, ["serious", "significant"]),
    (5.0, ["moderate"]),
    (3.0, ["minor", "limited"]),
]


def _extract_zone(text: str, zone_id: Optional[str]) -> str:
    if zone_id:
        return zone_id
    lowered = text.lower()
    for pattern, zid in ZONE_PATTERNS:
        if re.search(pattern, lowered):
            return zid
    return "ZONE_A"


def _extract_type(text: str) -> str:
    lowered = text.lower()
    for itype, words in TYPE_KEYWORDS.items():
        if any(w in lowered for w in words):
            return itype
    return "other"


def _extract_population(text: str) -> tuple[Optional[int], Optional[int]]:
    lowered = text.lower()
    numbers = []
    for match in re.finditer(r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:additional\s+)?(?:people|persons|residents|affected)", lowered):
        numbers.append(int(match.group(1).replace(",", "")))
    affected = numbers[0] if numbers else None
    vulnerable = None
    vuln_match = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:vulnerable|elderly|children)", lowered)
    if vuln_match:
        vulnerable = int(vuln_match.group(1).replace(",", ""))
    elif affected is not None:
        vulnerable = int(affected * 0.16)
    return affected, vulnerable


def _extract_severity(text: str) -> float:
    lowered = text.lower()
    for score, words in SEVERITY_KEYWORDS:
        if any(w in lowered for w in words):
            return score
    return 5.0


def analyze_report_heuristic(report_text: str, zone_id: Optional[str] = None) -> Dict:
    affected, vulnerable = _extract_population(report_text)
    incident_type = _extract_type(report_text)
    severity = _extract_severity(report_text)
    confidence = 0.62
    if affected is not None:
        confidence += 0.15
    if zone_id or re.search(r"zone\s*[a-e]\b", report_text.lower()):
        confidence += 0.1
    confidence = min(confidence, 0.92)

    needs: List[Dict] = []
    if incident_type in ("flood", "landslide", "earthquake") or severity >= 7:
        needs.append({"type": "rescue_team", "quantity": None, "known": False})
    if "water" in report_text.lower() or incident_type == "flood":
        needs.append({"type": "water_liter", "quantity": None, "known": False})

    return {
        "zone_id": _extract_zone(report_text, zone_id),
        "incident_type": incident_type,
        "affected_population": affected,
        "vulnerable_population": vulnerable,
        "severity": severity,
        "required_resource_types": [n["type"] for n in needs] or ["rescue_team", "medical_kit"],
        "needs": needs,
        "confidence": round(confidence, 2),
        "source_mode": "HEURISTIC",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "situation",
    }


def duplicate_status_heuristic(new_report: str, existing_incidents: List[Dict], zone_id: str, incident_type: str) -> Dict:
    if not existing_incidents:
        return {
            "is_duplicate": False,
            "duplicate_status": "NEW",
            "matched_incidents": [],
            "similarity_score": 0.0,
            "explanation": "No existing incidents to compare",
            "agent": "duplicate_detection",
        }

    new_tokens = set(re.findall(r"[a-z0-9]+", new_report.lower()))
    best = {"score": 0.0, "id": None, "reasons": []}

    for inc in existing_incidents:
        score = 0.0
        reasons = []
        if inc.get("zone_id") == zone_id:
            score += 0.35
            reasons.append("same zone")
        if inc.get("incident_type") == incident_type and incident_type != "other":
            score += 0.25
            reasons.append("same incident type")
        existing_tokens = set(re.findall(r"[a-z0-9]+", (inc.get("report_text") or "").lower()))
        if new_tokens and existing_tokens:
            overlap = len(new_tokens & existing_tokens) / max(len(new_tokens | existing_tokens), 1)
            score += overlap * 0.4
            if overlap >= 0.3:
                reasons.append(f"{int(overlap * 100)}% text overlap")
        ts = inc.get("timestamp")
        if ts:
            try:
                then = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if then.tzinfo is None:
                    then = then.replace(tzinfo=timezone.utc)
                minutes = abs((datetime.now(timezone.utc) - then).total_seconds()) / 60
                if minutes <= 30:
                    score += 0.15
                    reasons.append(f"{int(minutes)}-minute interval")
            except Exception:
                pass
        if score > best["score"]:
            best = {"score": score, "id": inc.get("id"), "reasons": reasons}

    status = "NEW"
    is_dup = False
    if best["score"] >= 0.8:
        status = "CONFIRMED_DUPLICATE"
        is_dup = True
    elif best["score"] >= 0.5:
        status = "POSSIBLE_DUPLICATE"

    explanation = "No matching active incident"
    if best["id"]:
        explanation = f"Reports compared with {best['id']}: " + (", ".join(best["reasons"]) or "low similarity")
        if status != "NEW":
            explanation = f"{status.replace('_', ' ').title()}: {explanation} ({best['score']:.0%} similarity)"

    return {
        "is_duplicate": is_dup,
        "duplicate_status": status,
        "matched_incidents": [best["id"]] if best["id"] and status != "NEW" else [],
        "similarity_score": round(best["score"], 2),
        "explanation": explanation,
        "agent": "duplicate_detection",
    }
