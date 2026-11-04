"""
agents/scenario_simulation_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 4 — Scenario Simulation Agent.
          Constructs BAU and intervention scenarios and runs numerical simulations.
          Enables organizations to compare decarbonization pathway options.

Agent Responsibilities:
    - Build Business-As-Usual (BAU) projection
    - Apply selected strategies to model intervention curve
    - Report projected reductions and net-zero trajectory

Dependencies: tools/scenario_simulator.py
"""

from __future__ import annotations

from typing import Any

from tools.scenario_simulator import simulate_scenario
from utils.logger import get_logger

log = get_logger("ScenarioSimulationAgent")


class ScenarioSimulationAgent:
    """
    Agent 4: Runs decarbonization scenario simulations.

    Called by: SupervisorAgent
    Calls:     simulate_scenario() tool
    """

    AGENT_NAME = "Scenario Simulation Agent"

    def run(
        self,
        accounting_result: dict[str, Any],
        scored_strategies: list[dict[str, Any]],
        scenario_name: str = "Intervention Scenario",
        years: int = 3,
    ) -> dict[str, Any]:
        """
        Simulate BAU vs. intervention scenarios.

        Args:
            accounting_result:  From CarbonAccountingAgent — provides baseline tCO₂e.
            scored_strategies:  From CostFeasibilityAgent — strategies with feasibility scores.
            scenario_name:      Label for this scenario.
            years:              Simulation horizon in years.

        Returns:
            {
                "bau":               simulation result for BAU (no strategies)
                "intervention":      simulation result applying all High/Medium priority strategies
                "scenarios_compared": list of both for display
                "narrative":          str — explainability text
                "agent":              str
            }
        """
        log.info(
            f"{self.AGENT_NAME} invoked — simulating {years}-year horizon",
            extra={"action": "agent_start", "agent": self.AGENT_NAME}
        )

        baseline = accounting_result.get("total_tco2e", 0.0)

        # ── BAU Scenario ──────────────────────────────────────────────────
        bau_result = simulate_scenario(
            baseline_tco2e=baseline,
            strategies_applied=[],  # No interventions
            years=years,
        )
        bau_result["scenario_name"] = "Business As Usual (No Action)"
        bau_result["scenario_type"] = "bau"

        # ── Intervention Scenario — apply High + Medium priority strategies ──
        actionable = [
            s for s in scored_strategies
            if s.get("priority") in ("High", "Medium")
        ]
        intervention_result = simulate_scenario(
            baseline_tco2e=baseline,
            strategies_applied=actionable,
            years=years,
        )
        intervention_result["scenario_name"] = scenario_name
        intervention_result["scenario_type"] = "intervention"
        intervention_result["strategies_applied_count"] = len(actionable)

        # ── Narrative (Explainability) ────────────────────────────────────
        reduction_pct = intervention_result.get("total_reduction_pct", 0.0)
        net_zero = intervention_result.get("net_zero_year")

        narrative = (
            f"Scenario '{scenario_name}' applies {len(actionable)} high/medium priority strategies "
            f"against a baseline of {baseline:,.2f} tCO₂e. "
            f"Projected cumulative reduction over {years} years: {reduction_pct:.1f}%. "
        )
        if net_zero:
            narrative += f"Net-zero trajectory projected by {net_zero}. "
        else:
            narrative += (
                "Net-zero is not achievable within this planning horizon with current strategies. "
                "Additional high-impact interventions are recommended."
            )

        result = {
            "bau":                bau_result,
            "intervention":       intervention_result,
            "scenarios_compared": [bau_result, intervention_result],
            "narrative":          narrative,
            "baseline_tco2e":     baseline,
            "years":              years,
            "agent":              self.AGENT_NAME,
        }

        log.info(
            f"{self.AGENT_NAME} complete. Reduction: {reduction_pct:.1f}%",
            extra={"action": "agent_complete",
                   "outputs": {"reduction_pct": reduction_pct, "net_zero_year": net_zero}}
        )
        return result
