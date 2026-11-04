"""
agents/emissions_analysis_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 2 — Emissions Analysis Agent.
          Identifies and ranks carbon hotspots from accounting results.
          Compares emissions across business units and scope categories.

Agent Responsibilities:
    - Rank top emission hotspots by tCO₂e
    - Compute percentage contributions
    - Summarize by scope and business unit
    - Flag high-emission activities for escalation

Dependencies: tools/hotspot_identifier.py
"""

from __future__ import annotations

from typing import Any

from tools.hotspot_identifier import (
    identify_hotspots,
    summarize_by_scope,
    summarize_by_business_unit,
)
from utils.logger import get_logger

log = get_logger("EmissionsAnalysisAgent")

# Threshold above which an organization is flagged as "high-emission"
# and the HITL gate is triggered (guideline §4.7 — human-in-the-loop)
HIGH_EMISSION_THRESHOLD_TCO2E = 5_000.0


class EmissionsAnalysisAgent:
    """
    Autonomous AI agent responsible for emissions hotspot analysis.

    Called by: SupervisorAgent
    Calls:     identify_hotspots(), summarize_by_scope(), summarize_by_business_unit()
    """

    AGENT_NAME = "Emissions Analysis Agent"

    def run(
        self,
        emissions_result: dict[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        """
        Analyse emissions data to identify hotspots.

        Args:
            emissions_result: Output from CarbonAccountingAgent.run()
            top_n:            Number of top hotspots to surface (default 5)

        Returns:
            {
                "hotspots":          list of ranked hotspot dicts
                "scope_breakdown":   list of scope summary dicts
                "bu_breakdown":      list of business unit summary dicts
                "total_tco2e":       float
                "high_emission_flag": bool   # triggers HITL if True
                "agent":             str
                "analysis_narrative": str    # explainability text
            }
        """
        log.info(
            "Emissions Analysis Agent invoked",
            extra={"action": "agent_start", "agent": self.AGENT_NAME}
        )

        total_tco2e  = emissions_result.get("total_tco2e", 0.0)
        hotspots     = identify_hotspots(emissions_result, top_n=top_n)
        scope_summary = summarize_by_scope(emissions_result)
        bu_summary   = summarize_by_business_unit(emissions_result)

        # Flag high-emission organizations for HITL
        high_emission = total_tco2e >= HIGH_EMISSION_THRESHOLD_TCO2E

        # Build explainability narrative
        if hotspots:
            top = hotspots[0]
            narrative = (
                f"Analysis identified {len(hotspots)} key emission hotspots from a total of "
                f"{total_tco2e:,.2f} tCO₂e. "
                f"The largest single source is '{top['activity']}' in {top['scope']}, "
                f"contributing {top['pct_contribution']:.1f}% of total emissions "
                f"({top['tco2e']:,.2f} tCO₂e). "
            )
            if high_emission:
                narrative += (
                    f"⚠️ ESCALATION: Total emissions exceed {HIGH_EMISSION_THRESHOLD_TCO2E:,.0f} tCO₂e. "
                    "Human review is required before the ESG roadmap is finalized."
                )
        else:
            narrative = "No emission data available for hotspot analysis."

        result = {
            "hotspots":           hotspots,
            "scope_breakdown":    scope_summary,
            "bu_breakdown":       bu_summary,
            "total_tco2e":        total_tco2e,
            "high_emission_flag": high_emission,
            "agent":              self.AGENT_NAME,
            "analysis_narrative": narrative,
        }

        log.info(
            f"Analysis complete. {len(hotspots)} hotspots identified. "
            f"High emission flag: {high_emission}",
            extra={
                "action":  "agent_complete",
                "outputs": {"hotspot_count": len(hotspots), "high_emission": high_emission}
            }
        )
        return result
