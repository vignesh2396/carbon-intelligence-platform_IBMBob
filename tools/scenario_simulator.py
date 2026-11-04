"""
tools/scenario_simulator.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Tool 4 — Numerical decarbonization scenario simulation engine.
          Models Business-As-Usual (BAU) vs. intervention pathways.
          Called by the Scenario Simulation Agent.

Design:   Pure numeric simulation — no LLM dependency.
          Returns year-by-year emission curves for visualization.

Dependencies: None (standard library only)
"""

from __future__ import annotations

import math
from typing import Any
from utils.logger import get_logger

log = get_logger("ScenarioSimulatorTool")

# ── BAU Growth Rate Assumptions ───────────────────────────────────────────────
# Default: 2% annual emission growth if no intervention (conservative corporate average)
BAU_GROWTH_RATE = 0.02


def simulate_scenario(
    baseline_tco2e: float,
    strategies_applied: list[dict[str, Any]],
    years: int = 3,
    bau_growth_rate: float = BAU_GROWTH_RATE,
) -> dict[str, Any]:
    """
    Simulate a decarbonization scenario against a Business-As-Usual baseline.

    Args:
        baseline_tco2e:      Current year total tCO₂e.
        strategies_applied:  List of strategy dicts with 'estimated_reduction_tco2e'
                             and 'timeframe' (e.g. "1 year", "3 years").
        years:               Number of years to simulate (default 3).
        bau_growth_rate:     Annual BAU emission growth rate (default 2%).

    Returns:
        {
            "bau_curve":            list[float],    # tCO₂e per year, BAU
            "intervention_curve":   list[float],    # tCO₂e per year, with strategies
            "year_labels":          list[str],
            "total_bau_tco2e":      float,          # cumulative BAU over period
            "total_intervention_tco2e": float,       # cumulative with interventions
            "total_reduction_tco2e": float,
            "total_reduction_pct":  float,
            "net_zero_year":        str | None,     # projected year to reach net zero
        }
    """
    year_labels = [f"Year {i}" for i in range(years + 1)]

    # BAU curve: exponential growth from baseline
    bau_curve = [
        round(baseline_tco2e * ((1 + bau_growth_rate) ** yr), 2)
        for yr in range(years + 1)
    ]

    # Compute annual reductions from strategies
    # Strategy reductions are distributed based on their timeframe
    annual_reduction_map: dict[int, float] = {yr: 0.0 for yr in range(years + 1)}

    for strategy in strategies_applied:
        reduction = float(strategy.get("estimated_reduction_tco2e", 0))
        timeframe = str(strategy.get("timeframe", "1 year")).lower()

        # Parse timeframe: "1 year" → 1, "3 years" → 3, "2-3 years" → 2
        try:
            tf_years = int(timeframe.split()[0].split("-")[0])
        except (ValueError, IndexError):
            tf_years = 1

        # Apply reduction linearly from the implementation year onwards
        tf_years = max(1, min(tf_years, years))
        annual_share = reduction / tf_years
        for yr in range(tf_years, years + 1):
            annual_reduction_map[yr] += annual_share

    # Intervention curve: BAU minus cumulative reductions
    intervention_curve = []
    cumulative_reduction = 0.0
    for yr in range(years + 1):
        cumulative_reduction += annual_reduction_map[yr]
        val = max(0.0, round(bau_curve[yr] - cumulative_reduction, 2))
        intervention_curve.append(val)

    # KPIs
    total_bau           = sum(bau_curve[1:])   # exclude year 0
    total_intervention  = sum(intervention_curve[1:])
    total_reduction     = total_bau - total_intervention
    reduction_pct       = round((total_reduction / total_bau) * 100, 1) if total_bau else 0.0

    # Net zero projection: first year where intervention_curve ≈ 0
    net_zero_year: str | None = None
    for i, val in enumerate(intervention_curve):
        if val < baseline_tco2e * 0.05:   # < 5% of baseline ≈ net zero threshold
            net_zero_year = year_labels[i]
            break

    result = {
        "bau_curve":                [round(v, 2) for v in bau_curve],
        "intervention_curve":       [round(v, 2) for v in intervention_curve],
        "year_labels":              year_labels,
        "total_bau_tco2e":          round(total_bau, 2),
        "total_intervention_tco2e": round(total_intervention, 2),
        "total_reduction_tco2e":    round(total_reduction, 2),
        "total_reduction_pct":      reduction_pct,
        "net_zero_year":            net_zero_year,
    }

    log.info(
        f"Scenario simulated: {reduction_pct:.1f}% reduction over {years} years",
        extra={"action": "scenario_simulated", "outputs": {
            "reduction_pct": reduction_pct,
            "net_zero_year": net_zero_year
        }}
    )
    return result
