"""
agents/supervisor_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Supervisor Agent — the orchestration brain of the multi-agent system.
          Routes tasks to specialized agents in the correct sequence,
          maintains session state, and enforces the Human-in-the-Loop gate.

This implements Guideline §4 requirements:
    ✓ Multiple Agent Roles (6 specialized agents)
    ✓ Multi-step reasoning workflow (sequential orchestration)
    ✓ Agent memory/state (AgentState dataclass)
    ✓ Human-in-the-Loop (HITL gate before roadmap export)
    ✓ Explainability (narrative from each agent propagated to UI)

Architecture: Supervisor pattern (not LangGraph graph for simplicity in
              the 4-day prototype; can be migrated to LangGraph graph later).

Dependencies: All specialized agents
"""

from __future__ import annotations

import os
import pandas as pd
from dataclasses import dataclass, field
from typing import Any, Optional

from agents.carbon_accounting_agent    import CarbonAccountingAgent
from agents.emissions_analysis_agent  import EmissionsAnalysisAgent
from agents.reduction_strategy_agent  import ReductionStrategyAgent
from agents.scenario_simulation_agent import ScenarioSimulationAgent
from agents.cost_feasibility_agent    import CostFeasibilityAgent
from agents.esg_roadmap_agent         import ESGRoadmapAgent
from utils.logger import get_logger

log = get_logger("SupervisorAgent")


@dataclass
class AgentState:
    """
    Holds all intermediate results across the multi-step agent pipeline.
    This is the "agent memory" required by Guideline §4.5.
    """
    org_name:           str              = "Organization"
    activity_df:        Optional[Any]    = None   # pandas DataFrame

    # Step results — populated sequentially by the supervisor
    accounting_result:   dict = field(default_factory=dict)
    analysis_result:     dict = field(default_factory=dict)
    strategy_result:     dict = field(default_factory=dict)
    feasibility_result:  dict = field(default_factory=dict)
    scenario_result:     dict = field(default_factory=dict)
    roadmap_result:      dict = field(default_factory=dict)

    # Pipeline control
    current_step:        str  = "idle"
    hitl_required:       bool = False
    hitl_approved:       bool = False
    errors:              list = field(default_factory=list)
    completed_steps:     list = field(default_factory=list)

    # User-configurable inputs
    budget_usd:          float = 500_000.0
    target_year:         int   = 2030
    simulation_years:    int   = 3


class SupervisorAgent:
    """
    Orchestrates the full multi-agent pipeline.

    Workflow:
        1. Carbon Accounting Agent    → emissions inventory
        2. Emissions Analysis Agent   → hotspot identification
        3. Reduction Strategy Agent   → RAG-grounded strategies
        4. Cost & Feasibility Agent   → strategy scoring
        5. Scenario Simulation Agent  → BAU vs. intervention
        6. ESG Roadmap Agent          → roadmap draft (AWAITING_APPROVAL)
        ─ HITL GATE ─────────────────────────────────────────────
        7. Human Approves → roadmap exported
    """

    def __init__(self) -> None:
        self._accounting_agent   = CarbonAccountingAgent()
        self._analysis_agent     = EmissionsAnalysisAgent()
        self._strategy_agent     = ReductionStrategyAgent()
        self._feasibility_agent  = CostFeasibilityAgent()
        self._scenario_agent     = ScenarioSimulationAgent()
        self._roadmap_agent      = ESGRoadmapAgent()

    def run_full_pipeline(
        self,
        activity_df: pd.DataFrame,
        org_name: str = "Organization",
        budget_usd: float = 500_000.0,
        target_year: int = 2030,
        simulation_years: int = 3,
        progress_callback=None,
    ) -> AgentState:
        """
        Execute the full 6-agent pipeline sequentially.

        Args:
            activity_df:        Validated emissions activity DataFrame
            org_name:           Organization name for reporting
            budget_usd:         Available investment budget (USD)
            target_year:        Net-zero target year
            simulation_years:   Scenario simulation horizon
            progress_callback:  Optional callable(step_name, step_number, total_steps)
                                for Streamlit progress updates

        Returns:
            AgentState with all results populated.
            Check state.hitl_required to determine if HITL gate is active.
        """
        state = AgentState(
            org_name=org_name,
            activity_df=activity_df,
            budget_usd=budget_usd,
            target_year=target_year,
            simulation_years=simulation_years,
        )

        steps = [
            ("Carbon Accounting",    self._run_accounting),
            ("Emissions Analysis",   self._run_analysis),
            ("Strategy Generation",  self._run_strategies),
            ("Cost & Feasibility",   self._run_feasibility),
            ("Scenario Simulation",  self._run_scenarios),
            ("ESG Roadmap Draft",    self._run_roadmap),
        ]
        total = len(steps)

        for i, (step_name, step_fn) in enumerate(steps, 1):
            log.info(f"[{i}/{total}] Executing: {step_name}",
                     extra={"action": "supervisor_step", "step": step_name})
            if progress_callback:
                progress_callback(step_name, i, total)

            state.current_step = step_name
            try:
                step_fn(state)
                state.completed_steps.append(step_name)
            except Exception as e:
                error_msg = f"Step '{step_name}' failed: {e}"
                log.warning(error_msg, extra={"action": "step_error", "warning": str(e)})
                state.errors.append(error_msg)
                # Continue pipeline where possible; only abort if accounting fails
                if step_name == "Carbon Accounting":
                    state.current_step = "error"
                    return state

        # ── HITL Gate Assessment ──────────────────────────────────────────
        state.hitl_required = (
            state.analysis_result.get("high_emission_flag", False)
            or state.roadmap_result.get("status") == "AWAITING_APPROVAL"
        )
        state.current_step = "awaiting_human_approval" if state.hitl_required else "complete"

        log.info(
            f"Pipeline complete. HITL required: {state.hitl_required}",
            extra={"action": "pipeline_complete",
                   "outputs": {"steps_completed": len(state.completed_steps),
                               "hitl_required": state.hitl_required}}
        )
        return state

    # ── Individual Step Runners ───────────────────────────────────────────────

    def _run_accounting(self, state: AgentState) -> None:
        state.accounting_result = self._accounting_agent.run(state.activity_df)

    def _run_analysis(self, state: AgentState) -> None:
        state.analysis_result = self._analysis_agent.run(state.accounting_result)

    def _run_strategies(self, state: AgentState) -> None:
        state.strategy_result = self._strategy_agent.run(state.analysis_result)

    def _run_feasibility(self, state: AgentState) -> None:
        state.feasibility_result = self._feasibility_agent.run(
            state.strategy_result,
            budget_usd=state.budget_usd,
        )

    def _run_scenarios(self, state: AgentState) -> None:
        state.scenario_result = self._scenario_agent.run(
            state.accounting_result,
            state.feasibility_result.get("scored_strategies", []),
            years=state.simulation_years,
        )

    def _run_roadmap(self, state: AgentState) -> None:
        state.roadmap_result = self._roadmap_agent.run(
            org_name=state.org_name,
            accounting_result=state.accounting_result,
            feasibility_result=state.feasibility_result,
            scenario_result=state.scenario_result,
            target_year=state.target_year,
        )

    # ── HITL: Human Approval ──────────────────────────────────────────────────

    def approve_roadmap(self, state: AgentState, approved_by: str = "Human Reviewer") -> AgentState:
        """
        Record human approval of the ESG roadmap.
        This unlocks roadmap export.

        Args:
            state:       Current AgentState
            approved_by: Name/role of the approver (for audit trail)

        Returns:
            Updated AgentState with roadmap status APPROVED and export_ready=True
        """
        state.roadmap_result["status"]       = "APPROVED"
        state.roadmap_result["export_ready"] = True
        state.roadmap_result["approved_by"]  = approved_by
        state.hitl_approved                  = True
        state.current_step                   = "complete"

        log.info(
            f"Roadmap APPROVED by {approved_by}",
            extra={"action": "hitl_approved", "approved_by": approved_by}
        )
        return state

    def reject_roadmap(self, state: AgentState, reason: str = "") -> AgentState:
        """
        Record human rejection — roadmap is not exported.
        """
        state.roadmap_result["status"]       = "REJECTED"
        state.roadmap_result["export_ready"] = False
        state.roadmap_result["rejection_reason"] = reason
        state.hitl_approved                  = False
        state.current_step                   = "rejected"

        log.info(
            f"Roadmap REJECTED. Reason: {reason}",
            extra={"action": "hitl_rejected", "reason": reason}
        )
        return state
