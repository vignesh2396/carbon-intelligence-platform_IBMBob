"""
tools/feasibility_scorer.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Tool 5 — Scores and ranks reduction strategies by a composite
          cost-effectiveness and feasibility metric.
          Called by the Cost & Feasibility Agent.

Scoring Formula:
    composite_score = (emission_reduction_weight × normalized_reduction)
                    + (feasibility_weight × feasibility_score)
                    - (cost_weight × normalized_cost)

    Where weights are configurable (default: 0.5 / 0.3 / 0.2)

Dependencies: None (standard library only)
"""

from __future__ import annotations

from typing import Any
from utils.logger import get_logger

log = get_logger("FeasibilityScorerTool")

# ── Scoring Weights ───────────────────────────────────────────────────────────
REDUCTION_WEIGHT  = 0.50
FEASIBILITY_WEIGHT = 0.30
COST_WEIGHT       = 0.20

# ── Default Fallback Values (when strategy data is incomplete) ────────────────
DEFAULT_REDUCTION_TCO2E = 50.0
DEFAULT_COST_USD        = 25_000.0
DEFAULT_FEASIBILITY     = 0.5


def score_feasibility(
    strategies: list[dict[str, Any]],
    budget_usd: float = 500_000.0,
    timeframe_years: int = 3,
) -> list[dict[str, Any]]:
    """
    Score and rank reduction strategies by composite cost-effectiveness.

    Args:
        strategies:       List of strategy dicts (from RAG agent or LLM).
        budget_usd:       Total available budget for the planning period (USD).
        timeframe_years:  Target timeframe for implementation (years).

    Returns:
        Strategies sorted by composite_score descending, each enriched with:
        {
            ...original strategy fields...
            "composite_score":    float (0–1),
            "cost_per_tco2e":     float (USD/tCO₂e),
            "within_budget":      bool,
            "priority":           str ("High" | "Medium" | "Low"),
            "recommendation":     str
        }
    """
    if not strategies:
        return []

    # Extract raw values with safe defaults
    reductions = [
        float(s.get("estimated_reduction_tco2e", DEFAULT_REDUCTION_TCO2E))
        for s in strategies
    ]
    costs = [
        float(s.get("estimated_cost_usd", DEFAULT_COST_USD))
        for s in strategies
    ]
    feasibilities = [
        float(s.get("feasibility_score", DEFAULT_FEASIBILITY))
        for s in strategies
    ]

    # Normalize to [0, 1]
    max_reduction = max(reductions) if max(reductions) > 0 else 1.0
    max_cost      = max(costs)      if max(costs) > 0      else 1.0

    scored: list[dict[str, Any]] = []

    for i, strategy in enumerate(strategies):
        reduction     = reductions[i]
        cost          = costs[i]
        feasibility   = feasibilities[i]

        norm_reduction = reduction / max_reduction
        norm_cost      = cost / max_cost

        composite = (
            REDUCTION_WEIGHT  * norm_reduction
            + FEASIBILITY_WEIGHT * feasibility
            - COST_WEIGHT     * norm_cost
        )
        composite = max(0.0, min(1.0, composite))  # clamp to [0, 1]

        cost_per_tco2e = round(cost / reduction, 2) if reduction > 0 else float("inf")
        within_budget  = cost <= budget_usd

        # Priority labelling
        if composite >= 0.65:
            priority = "High"
            recommendation = "Implement immediately — high impact, high feasibility."
        elif composite >= 0.40:
            priority = "Medium"
            recommendation = "Schedule for Year 2 — moderate impact, plan resources."
        else:
            priority = "Low"
            recommendation = "Consider for Year 3+ — lower impact or higher cost."

        scored_strategy = {
            **strategy,
            "composite_score": round(composite, 3),
            "cost_per_tco2e":  cost_per_tco2e,
            "within_budget":   within_budget,
            "priority":        priority,
            "recommendation":  recommendation,
        }
        scored.append(scored_strategy)

    # Sort by composite score descending
    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    log.info(
        f"Scored {len(scored)} strategies. Top: '{scored[0].get('strategy_name', 'N/A')}' "
        f"(score={scored[0]['composite_score']:.3f})",
        extra={"action": "feasibility_scored", "strategy_count": len(scored)}
    )
    return scored
