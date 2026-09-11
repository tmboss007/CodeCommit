from typing import Dict, Optional, List
from openai import OpenAI
from anthropic import Anthropic
import json
import os

class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

        if self.provider == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate_structured(self, prompt: str, system: str = "") -> Dict:
        """Generate structured JSON output."""
        if self.provider == "openai":
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)

        elif self.provider == "anthropic":
            full_prompt = f"{system}\n\n{prompt}\n\nProvide response as valid JSON."
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.1,
                messages=[{"role": "user", "content": full_prompt}]
            )
            content = response.content[0].text
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)

class SituationAgent:
    """Extract structured information from incident reports."""

    def __init__(self):
        self.llm = LLMClient()

    def analyze_report(self, report_text: str, zone_id: Optional[str] = None) -> Dict:
        """
        Analyze incident report and extract structured information.

        Returns:
        {
            "zone_id": str,
            "incident_type": str,
            "affected_population": int,
            "vulnerable_population": int,
            "severity": float (0-10),
            "needs": [{"type": str, "quantity": int}],
            "confidence": float (0-1)
        }
        """
        system = """You are a disaster situation analysis agent. Extract structured information from incident reports.

Classify incident_type as one of: flood, earthquake, cyclone, fire, landslide, other

Severity scale (0-10):
0-2: Minor, limited impact
3-4: Moderate, localized damage
5-6: Serious, significant damage
7-8: Severe, widespread damage
9-10: Catastrophic, extreme damage

Estimate affected_population and vulnerable_population (elderly, children, disabled) if mentioned.
Identify needed resource types: rescue_team, medical_kit, water_liter, food_packet, shelter_capacity

Return valid JSON only."""

        prompt = f"""Analyze this incident report:

Report: {report_text}
{f"Zone: {zone_id}" if zone_id else ""}

Extract:
- incident_type
- affected_population (estimate if not explicit)
- vulnerable_population (estimate ~15-20% if not mentioned)
- severity (0-10 scale)
- needs (list of resource types needed)
- confidence (how confident in this analysis, 0-1)

JSON format:
{{
    "zone_id": "{zone_id or 'unknown'}",
    "incident_type": "flood",
    "affected_population": 1000,
    "vulnerable_population": 150,
    "severity": 7.5,
    "needs": [{{"type": "rescue_team", "quantity": 3}}],
    "confidence": 0.85
}}"""

        try:
            result = self.llm.generate_structured(prompt, system)
            result["agent"] = "situation"
            return result
        except Exception as e:
            # Fallback to default structure
            return {
                "zone_id": zone_id or "unknown",
                "incident_type": "other",
                "affected_population": 500,
                "vulnerable_population": 75,
                "severity": 5.0,
                "needs": [{"type": "rescue_team", "quantity": 1}],
                "confidence": 0.3,
                "agent": "situation",
                "error": str(e)
            }

class DuplicateDetectionAgent:
    """Detect duplicate or overlapping incident reports."""

    def __init__(self):
        self.llm = LLMClient()

    def check_duplicate(
        self,
        new_report: str,
        existing_incidents: List[Dict]
    ) -> Dict:
        """
        Check if new report is duplicate of existing incidents.

        Returns:
        {
            "is_duplicate": bool,
            "matched_incidents": [str],  # incident IDs
            "similarity_score": float,
            "explanation": str
        }
        """
        if not existing_incidents:
            return {
                "is_duplicate": False,
                "matched_incidents": [],
                "similarity_score": 0.0,
                "explanation": "No existing incidents to compare"
            }

        system = """You are a duplicate incident detection agent. Determine if a new report describes the same incident as existing reports.

Consider:
- Geographic proximity (same zone)
- Time proximity (within hours)
- Incident type
- Semantic similarity of descriptions

is_duplicate = true only if HIGH confidence (>0.8) same incident
similarity_score = 0.0 to 1.0"""

        existing_summary = "\n".join([
            f"ID: {inc['id']}, Zone: {inc.get('zone_id')}, Type: {inc.get('incident_type')}, "
            f"Time: {inc.get('timestamp')}, Report: {inc.get('report_text', '')[:100]}..."
            for inc in existing_incidents[:5]  # Limit to 5 most recent
        ])

        prompt = f"""New report: {new_report}

Existing incidents:
{existing_summary}

Analyze if new report duplicates any existing incident.

JSON format:
{{
    "is_duplicate": false,
    "matched_incidents": [],
    "similarity_score": 0.75,
    "explanation": "Similar to incident X but different location"
}}"""

        try:
            result = self.llm.generate_structured(prompt, system)
            result["agent"] = "duplicate_detection"
            return result
        except Exception as e:
            return {
                "is_duplicate": False,
                "matched_incidents": [],
                "similarity_score": 0.0,
                "explanation": f"Analysis failed: {str(e)}",
                "agent": "duplicate_detection"
            }

class CoordinationAgent:
    """Generate actionable tasks for agencies."""

    def generate_tasks(
        self,
        allocations: List[Dict],
        resources_map: Dict[str, Dict],
        zones_map: Dict[str, Dict],
        agencies_map: Dict[str, Dict]
    ) -> List[Dict]:
        """Generate coordination tasks from allocations."""
        tasks = []

        for alloc in allocations:
            resource = resources_map.get(alloc['resource_id'])
            zone = zones_map.get(alloc['zone_id'])

            if not resource or not zone:
                continue

            agency = agencies_map.get(resource['agency_id'])
            if not agency:
                continue

            action = self._format_action(resource, zone, alloc)

            tasks.append({
                "agency_id": agency['id'],
                "allocation_id": alloc['id'],
                "action": action,
                "status": "pending"
            })

        return tasks

    def _format_action(self, resource: Dict, zone: Dict, allocation: Dict) -> str:
        """Format human-readable action description."""
        qty_str = f"{allocation.get('quantity', 1)} {resource.get('unit', 'unit(s)')}" if allocation.get('quantity') else ""
        eta_str = f"ETA: {allocation.get('eta_minutes', 'unknown')} minutes" if allocation.get('eta_minutes') else ""

        return f"Deploy {resource['name']} {qty_str} to {zone['name']}. {eta_str}. Priority: {allocation.get('priority', 'N/A')}"
