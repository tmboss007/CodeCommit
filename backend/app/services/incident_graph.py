"""LangGraph wrapper around OrchestrationService incident steps.

Does not own commits, approval, or SSE. Nodes call existing methods.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph


class IncidentGraphState(TypedDict, total=False):
    orchestrator: Any
    report_text: str
    source: str
    zone_id: Optional[str]
    correlation_id: str
    auto_replan: bool
    old_snapshot: Dict[str, Any]
    structured_incident: Dict[str, Any]
    duplicate_result: Dict[str, Any]
    incident_id: str
    needs_list: List[Dict[str, Any]]
    needs_created: int
    zone_priority: Any
    priority_breakdown: Any
    old_priority: Any
    replan_required: bool
    replanning_reason: str
    replan_details: Dict[str, Any]
    optimization_result: Dict[str, Any]
    current_plan: Dict[str, Any]
    coordination_tasks: List[Dict[str, Any]]
    errors: List[str]


def _failed(state: IncidentGraphState) -> bool:
    return bool(state.get("errors"))


def situation_node(state: IncidentGraphState) -> Dict[str, Any]:
    orch = state["orchestrator"]
    try:
        structured = orch.situation_step(
            report_text=state["report_text"],
            source=state["source"],
            zone_id=state.get("zone_id"),
            correlation_id=state["correlation_id"],
        )
        return {"structured_incident": structured}
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"situation: {exc}"]}


def duplicate_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {}
    orch = state["orchestrator"]
    try:
        return {
            "duplicate_result": orch.duplicate_step(
                report_text=state["report_text"],
                structured=state["structured_incident"],
                correlation_id=state["correlation_id"],
            )
        }
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"duplicate: {exc}"]}


def needs_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {}
    orch = state["orchestrator"]
    try:
        incident_id, needs = orch.needs_step(
            report_text=state["report_text"],
            source=state["source"],
            structured=state["structured_incident"],
            duplicate_result=state["duplicate_result"],
            correlation_id=state["correlation_id"],
        )
        return {"incident_id": incident_id, "needs_list": needs, "needs_created": len(needs)}
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"needs: {exc}"]}


def priority_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {}
    orch = state["orchestrator"]
    try:
        priority, breakdown, old_priority = orch.priority_step(
            incident_id=state["incident_id"],
            correlation_id=state["correlation_id"],
        )
        return {"zone_priority": priority, "priority_breakdown": breakdown, "old_priority": old_priority}
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"priority: {exc}"]}


def replanning_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {"replan_required": False, "auto_replan": False}
    orch = state["orchestrator"]
    try:
        should, reason, details = orch.replanning_step(
            old_snapshot=state["old_snapshot"],
            old_priority=state.get("old_priority"),
            incident_id=state["incident_id"],
            auto_replan=state.get("auto_replan", True),
            correlation_id=state["correlation_id"],
        )
        return {
            "replan_required": should,
            "replanning_reason": reason,
            "replan_details": details,
            "auto_replan": state.get("auto_replan", True),
        }
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"replanning: {exc}"], "replan_required": False, "auto_replan": False}


def after_replanning(state: IncidentGraphState) -> str:
    if _failed(state):
        return "end"
    if state.get("replan_required") and state.get("auto_replan"):
        return "optimize"
    return "end"


def optimization_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {}
    orch = state["orchestrator"]
    try:
        packed = orch.optimization_step(
            correlation_id=state["correlation_id"],
            trigger=state.get("replanning_reason") or "replan",
            prior_snapshot=state.get("old_snapshot"),
        )
        return {"optimization_result": packed}
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"optimization: {exc}"]}


def coordination_node(state: IncidentGraphState) -> Dict[str, Any]:
    if _failed(state):
        return {}
    orch = state["orchestrator"]
    try:
        plan = orch.coordination_step(state["optimization_result"])
        return {"current_plan": plan, "coordination_tasks": plan.get("coordination_tasks") or []}
    except Exception as exc:
        orch.abort_pipeline()
        return {"errors": [f"coordination: {exc}"]}


def build_incident_graph():
    workflow = StateGraph(IncidentGraphState)
    workflow.add_node("situation", situation_node)
    workflow.add_node("duplicate", duplicate_node)
    workflow.add_node("needs", needs_node)
    workflow.add_node("priority", priority_node)
    workflow.add_node("replanning", replanning_node)
    workflow.add_node("optimization", optimization_node)
    workflow.add_node("coordination", coordination_node)
    workflow.set_entry_point("situation")
    workflow.add_edge("situation", "duplicate")
    workflow.add_edge("duplicate", "needs")
    workflow.add_edge("needs", "priority")
    workflow.add_edge("priority", "replanning")
    workflow.add_conditional_edges(
        "replanning",
        after_replanning,
        {"optimize": "optimization", "end": END},
    )
    workflow.add_edge("optimization", "coordination")
    workflow.add_edge("coordination", END)
    return workflow.compile()


INCIDENT_GRAPH = None


def get_incident_graph():
    global INCIDENT_GRAPH
    if INCIDENT_GRAPH is None:
        INCIDENT_GRAPH = build_incident_graph()
    return INCIDENT_GRAPH


def run_incident_pipeline(orchestrator, *, report_text, source, zone_id, correlation_id, auto_replan) -> IncidentGraphState:
    graph = get_incident_graph()
    return graph.invoke(
        {
            "orchestrator": orchestrator,
            "report_text": report_text,
            "source": source,
            "zone_id": zone_id,
            "correlation_id": correlation_id,
            "auto_replan": auto_replan,
            "old_snapshot": orchestrator._current_snapshot(),
            "errors": [],
            "replan_required": False,
        }
    )
