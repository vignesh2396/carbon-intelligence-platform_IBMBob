"""
agents/cost_feasibility_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 5 — Cost & Feasibility Agent.
          Scores and ranks reduction strategies by cost-effectiveness.
          Provides prioritized investment recommendations for decision-makers.

Agent Responsibilities:
    - Apply composite scoring (reduction × feasibility / cost)
    - Rank strategies by ROI and practical feasibility
    - Flag strategies exceeding budget constraints
    - Provide "High / Medium / Low" priority labels

Dependencies: tools/feasibility_scorer.py
"""

from __future__ import annotations

from typing import Any

from tools.feasibility_scorer import score_feasibility
from utils.helpers import format_currency
from utils.logger import get_logger

log = get_logger("CostFeasibilityAgent")


class CostFeasibilityAgent:
    """
    Agent 5: Scores strategies for cost-effectiveness and feasibility.

    Called by: SupervisorAgent
    Calls:     score_feasibility() tool
    """

    AGENT_NAME = "Cost & Feasibility Agent"

    def run(
        self,
        strategy_result: dict[str, Any],
        budget_usd: float = 500_000.0,
        timeframe_years: int = 3,
    ) -> dict[str, Any]:
        """
        Score all generated strategies and produce ranked investment recommendations.

        Args:
            strategy_result:  From ReductionStrategyAgent.run()
            budget_usd:       Available budget for decarbonization investment (USD).
            timeframe_years:  Planning horizon for ROI calculation.

        Returns:
            {
                "scored_strategies":    list of scored+ranked strategy dicts
                "high_priority":        list — strategies with priority "High"
                "medium_priority":      list — strategies with priority "Medium"
                "low_priority":         list — strategies with priority "Low"
                "total_investment_required": float (sum of High+Medium strategy costs)
                "within_budget":        bool
                "budget_usd":           float
                "narrative":            str — explainability text
                "agent":                str
            }
        """
        log.info(
            f"{self.AGENT_NAME} invoked. Budget: {format_currency(budget_usd)}",
            extra={"action": "agent_start", "agent": self.AGENT_NAME,
                   "inputs": {"budget_usd": budget_usd}}
        )

        all_strategies = strategy_result.get("all_strategies", [])
        if not all_strategies:
            return {
                "scored_strategies": [],
                "high_priority": [],
                "medium_priority": [],
                "low_priority": [],
                "total_investment_required": 0.0,
                "within_budget": True,
                "budget_usd": budget_usd,
                "narrative": "No strategies available to score.",
                "agent": self.AGENT_NAME,
            }

        # ── Score and Rank ────────────────────────────────────────────────
        scored = score_feasibility(all_strategies, budget_usd, timeframe_years)

        high_priority   = [s for s in scored if s["priority"] == "High"]
        medium_priority = [s for s in scored if s["priority"] == "Medium"]
        low_priority    = [s for s in scored if s["priority"] == "Low"]

        investment_required = sum(
            float(s.get("estimated_cost_usd", 0))
            for s in high_priority + medium_priority
        )
        within_budget = investment_required <= budget_usd

        # ── Narrative ─────────────────────────────────────────────────────
        narrative = (
            f"Scored {len(scored)} strategies. "
            f"{len(high_priority)} are High priority, "
            f"{len(medium_priority)} Medium priority, "
            f"{len(low_priority)} Low priority. "
            f"Total investment for High+Medium strategies: {format_currency(investment_required)}. "
        )
        if within_budget:
            narrative += f"This is within the stated budget of {format_currency(budget_usd)}."
        else:
            narrative += (
                f"⚠️ This exceeds the stated budget of {format_currency(budget_usd)}. "
                "Consider phasing implementation or revising budget allocation."
            )

        result = {
            "scored_strategies":         scored,
            "high_priority":             high_priority,
            "medium_priority":           medium_priority,
            "low_priority":              low_priority,
            "total_investment_required": round(investment_required, 2),
            "within_budget":             within_budget,
            "budget_usd":                budget_usd,
            "narrative":                 narrative,
            "agent":                     self.AGENT_NAME,
        }

        log.info(
            f"{self.AGENT_NAME} complete. {len(high_priority)} high-priority strategies. "
            f"Investment required: {format_currency(investment_required)}",
            extra={"action": "agent_complete",
                   "outputs": {"strategy_count": len(scored),
                               "investment_usd": investment_required}}
        )
        return result
