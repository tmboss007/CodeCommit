from typing import Dict, List, Optional
import os
from app.services.situation_heuristic import analyze_report_heuristic, duplicate_status_heuristic

class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic. Optional — demo works without keys."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        self.client = None
        self.available = False

        if self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.available = True
        elif self.provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.available = True

    def generate_structured(self, prompt: str, system: str = "") -> Dict:
        if not self.available:
            raise RuntimeError("LLM provider not configured")
        import json

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

        full_prompt = f"{system}\n\n{prompt}\n\nProvide response as valid JSON."
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.1,
            messages=[{"role": "user", "content": full_prompt}]
        )
        content = response.content[0].text
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
        heuristic = analyze_report_heuristic(report_text, zone_id)
        if not self.llm.available:
            return heuristic

        system = """You are a disaster situation analysis agent. Extract structured information from incident reports.
Classify incident_type as one of: flood, earthquake, cyclone, fire, landslide, other
Severity scale (0-10). Do not invent exact population counts if they are not stated — use null.
Return valid JSON only."""

        prompt = f"""Analyze this incident report:

Report: {report_text}
{f"Zone: {zone_id}" if zone_id else ""}

JSON format:
{{
    "zone_id": "{zone_id or 'unknown'}",
    "incident_type": "flood",
    "affected_population": null,
    "vulnerable_population": null,
    "severity": 7.5,
    "required_resource_types": ["rescue_team"],
    "confidence": 0.85
}}"""
        try:
            result = self.llm.generate_structured(prompt, system)
            result["agent"] = "situation"
            result["source_mode"] = "LLM"
            if not result.get("zone_id") or result.get("zone_id") == "unknown":
                result["zone_id"] = heuristic["zone_id"]
            if result.get("affected_population") is None:
                result["affected_population"] = heuristic.get("affected_population")
            if result.get("vulnerable_population") is None:
                result["vulnerable_population"] = heuristic.get("vulnerable_population")
            return result
        except Exception as e:
            heuristic["error"] = str(e)
            return heuristic


class DuplicateDetectionAgent:
    """Hybrid duplicate detection: zone, time, type, text overlap. LLM optional."""

    def __init__(self):
        self.llm = LLMClient()

    def check_duplicate(
        self,
        new_report: str,
        existing_incidents: List[Dict],
        zone_id: str = "",
        incident_type: str = "other",
    ) -> Dict:
        heuristic = duplicate_status_heuristic(new_report, existing_incidents, zone_id, incident_type)
        if not existing_incidents or not self.llm.available:
            return heuristic
        try:
            result = self.llm.generate_structured(
                f"New report: {new_report}\nExisting: {existing_incidents[:5]}\nReturn JSON with is_duplicate, matched_incidents, similarity_score, explanation",
                "You detect duplicate disaster reports. is_duplicate true only if confidence > 0.8."
            )
            result["agent"] = "duplicate_detection"
            result.setdefault("duplicate_status", "CONFIRMED_DUPLICATE" if result.get("is_duplicate") else "NEW")
            return result
        except Exception:
            return heuristic


class CoordinationAgent:
    """Generate actionable tasks for agencies."""

    def generate_tasks(
        self,
        allocations: List[Dict],
        resources_map: Dict[str, Dict],
        zones_map: Dict[str, Dict],
        agencies_map: Dict[str, Dict]
    ) -> List[Dict]:
        tasks = []
        for alloc in allocations:
            resource = resources_map.get(alloc['resource_id'])
            zone = zones_map.get(alloc['zone_id'])
            if not resource or not zone:
                continue
            agency = agencies_map.get(resource['agency_id'])
            if not agency:
                continue
            tasks.append({
                "agency_id": agency['id'],
                "allocation_id": alloc['id'],
                "action": self._format_action(resource, zone, alloc),
                "status": "pending"
            })
        return tasks

    def _format_action(self, resource: Dict, zone: Dict, allocation: Dict) -> str:
        qty_str = f"{allocation.get('quantity', 1)} {resource.get('unit', 'unit(s)')}" if allocation.get('quantity') else ""
        eta_str = f"ETA: {allocation.get('eta_minutes', 'unknown')} minutes" if allocation.get('eta_minutes') else ""
        return f"Deploy {resource['name']} {qty_str} to {zone['name']}. {eta_str}. Priority: {allocation.get('priority', 'N/A')}"
