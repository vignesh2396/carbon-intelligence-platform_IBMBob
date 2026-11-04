"""
tools/hotspot_identifier.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Tool 2 — Identifies and ranks top carbon hotspots from emission results.
          Called by the Emissions Analysis Agent.
          Returns a ranked list of activities by tCO₂e contribution.

Design:   Pure function — stateless, fully testable.

Dependencies: utils/helpers.py
"""

from __future__ import annotations

from typing import Any
from utils.helpers import pct
from utils.logger import get_logger

log = get_logger("HotspotIdentifierTool")


def identify_hotspots(
    emissions_result: dict[str, Any],
    top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Identify and rank the top carbon emission hotspots.

    Args:
        emissions_result: Output from calculate_emissions() containing 'breakdown' list.
        top_n:            Number of top hotspots to return (default 5).

    Returns:
        List of hotspot dicts ranked by tCO₂e descending:
        [{
            "rank":             int,
            "activity":         str,
            "category":         str,
            "scope":            str,
            "business_unit":    str,
            "tco2e":            float,
            "pct_contribution": float,
        }]
    """
    breakdown  = emissions_result.get("breakdown", [])
    total_tco2e = emissions_result.get("total_tco2e", 0.0)

    if not breakdown:
        log.warning("No breakdown data to identify hotspots", extra={"action": "hotspot_empty"})
        return []

    # Sort by tCO₂e descending
    sorted_activities = sorted(breakdown, key=lambda x: x["tco2e"], reverse=True)

    hotspots: list[dict[str, Any]] = []
    for rank, item in enumerate(sorted_activities[:top_n], start=1):
        hotspot = {
            "rank":             rank,
            "activity":         item["activity"],
            "category":         item["category"],
            "scope":            item["scope"],
            "business_unit":    item["business_unit"],
            "tco2e":            item["tco2e"],
            "pct_contribution": pct(item["tco2e"], total_tco2e),
        }
        hotspots.append(hotspot)

    log.info(
        f"Identified {len(hotspots)} hotspots. Top: {hotspots[0]['activity']} ({hotspots[0]['tco2e']:.2f} tCO₂e)",
        extra={
            "action":  "hotspot_identified",
            "outputs": hotspots[:3]
        }
    )
    return hotspots


def summarize_by_scope(emissions_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return emissions summarized per scope for visualization.
    """
    scope_summary = emissions_result.get("scope_summary", {})
    total = emissions_result.get("total_tco2e", 0.0)
    return [
        {
            "scope": scope,
            "tco2e": tco2e,
            "pct":   pct(tco2e, total)
        }
        for scope, tco2e in scope_summary.items()
    ]


def summarize_by_business_unit(emissions_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return emissions summarized per business unit for visualization.
    """
    bu_summary = emissions_result.get("bu_summary", {})
    total = emissions_result.get("total_tco2e", 0.0)
    return sorted(
        [
            {
                "business_unit": bu,
                "tco2e": tco2e,
                "pct": pct(tco2e, total)
            }
            for bu, tco2e in bu_summary.items()
        ],
        key=lambda x: x["tco2e"],
        reverse=True
    )
