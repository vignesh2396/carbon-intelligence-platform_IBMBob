"""
agents/esg_roadmap_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 6 — ESG Roadmap Agent.
          Synthesizes all prior agent outputs into a structured, prioritized
          3-year net-zero decarbonization roadmap.

          The roadmap is NOT exported until a human approves it (HITL gate).
          This fulfills Guideline §4.7: Human-in-the-Loop requirement.

Agent Responsibilities:
    - Synthesize strategies into a phased roadmap
    - Map milestones and KPIs to each year
    - Generate an executive summary
    - Set roadmap status to AWAITING_APPROVAL until human approves

Dependencies: langchain_google_genai (for narrative generation)
"""

from __future__ import annotations

import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.logger import get_logger
from utils.helpers import format_tco2e, format_currency

log = get_logger("ESGRoadmapAgent")


ROADMAP_SYSTEM_PROMPT = """You are an expert ESG strategist and sustainability roadmap specialist.
Your task is to create a clear, structured, 3-year net-zero decarbonization roadmap.

RULES:
1. Organize the roadmap into Year 1, Year 2, Year 3 phases.
2. Each phase should list specific actions, expected tCO₂e reduction, and responsible parties.
3. Include KPIs for each phase.
4. End with an Executive Summary (3-4 sentences).
5. Use clear, non-technical language suitable for executive review.
6. Include a disclaimer: "This AI-generated roadmap requires validation by a certified sustainability professional before regulatory use."
7. Return plain text — not JSON, not markdown code blocks.
"""


class ESGRoadmapAgent:
    """
    Agent 6: Generates the final ESG decarbonization roadmap.

    Called by: SupervisorAgent
    Calls:     Gemini LLM for narrative synthesis
    Status:    Returns roadmap with status=AWAITING_APPROVAL (HITL gate)
    """

    AGENT_NAME = "ESG Roadmap Agent"

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set. Check your .env file.")
        self._llm = ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL", "gemini-1.5-pro"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            google_api_key=api_key,
        )

    def run(
        self,
        org_name: str,
        accounting_result: dict[str, Any],
        feasibility_result: dict[str, Any],
        scenario_result: dict[str, Any],
        target_year: int = 2030,
    ) -> dict[str, Any]:
        """
        Generate a prioritized 3-year ESG decarbonization roadmap.

        Returns:
            {
                "roadmap_text":   str   — formatted roadmap narrative
                "milestones":     list  — structured milestone list
                "kpis":           dict  — key performance indicators
                "status":         str   — "AWAITING_APPROVAL" (HITL gate)
                "export_ready":   bool  — False until human approves
                "agent":          str
            }
        """
        log.info(
            f"{self.AGENT_NAME} generating roadmap for {org_name}",
            extra={"action": "agent_start", "agent": self.AGENT_NAME}
        )

        total_tco2e   = accounting_result.get("total_tco2e", 0.0)
        high_priority = feasibility_result.get("high_priority", [])
        medium_priority = feasibility_result.get("medium_priority", [])
        investment    = feasibility_result.get("total_investment_required", 0.0)
        reduction_pct = scenario_result.get("intervention", {}).get("total_reduction_pct", 0.0)

        # ── Build structured milestones ───────────────────────────────────
        milestones = []
        year_buckets: dict[str, list] = {"Year 1": [], "Year 2": [], "Year 3": []}

        for s in high_priority:
            tf = str(s.get("timeframe", "1 year")).lower()
            year_buckets["Year 1"].append(s)

        for s in medium_priority:
            tf = str(s.get("timeframe", "2-3 years")).lower()
            if "1" in tf:
                year_buckets["Year 2"].append(s)
            else:
                year_buckets["Year 3"].append(s)

        for year, strategies in year_buckets.items():
            if strategies:
                phase_reduction = sum(float(s.get("estimated_reduction_tco2e", 0)) for s in strategies)
                milestones.append({
                    "phase":      year,
                    "actions":    [s.get("strategy_name", "Strategy") for s in strategies],
                    "tco2e_reduction": round(phase_reduction, 2),
                    "investment": round(sum(float(s.get("estimated_cost_usd", 0)) for s in strategies), 2),
                })

        # ── KPIs ──────────────────────────────────────────────────────────
        kpis = {
            "baseline_tco2e":             format_tco2e(total_tco2e),
            "projected_3yr_reduction_pct": f"{reduction_pct:.1f}%",
            "total_investment_required":   format_currency(investment),
            "target_year":                 str(target_year),
            "strategies_implemented":      len(high_priority) + len(medium_priority),
        }

        # ── LLM Narrative Generation ──────────────────────────────────────
        strategies_summary = "\n".join([
            f"- Year 1 (High Priority): " +
            ", ".join(s.get("strategy_name", "N/A") for s in high_priority[:3]),
            f"- Year 2-3 (Medium Priority): " +
            ", ".join(s.get("strategy_name", "N/A") for s in medium_priority[:3]),
        ])

        prompt = f"""
Create a 3-year ESG decarbonization roadmap for: {org_name}

CURRENT EMISSIONS: {format_tco2e(total_tco2e)}
PROJECTED REDUCTION: {reduction_pct:.1f}% over 3 years
TOTAL INVESTMENT: {format_currency(investment)}
TARGET NET ZERO YEAR: {target_year}

STRATEGIES TO IMPLEMENT:
{strategies_summary}

MILESTONES:
{chr(10).join(f"  {m['phase']}: {', '.join(m['actions'][:2])} — reduce by {format_tco2e(m['tco2e_reduction'])}" for m in milestones)}

Please generate the complete roadmap narrative.
"""
        try:
            response = self._llm.invoke([
                SystemMessage(content=ROADMAP_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            roadmap_text = response.content
        except Exception as e:
            log.warning(f"LLM roadmap generation failed: {e}",
                       extra={"action": "llm_error", "warning": str(e)})
            roadmap_text = self._fallback_roadmap(
                org_name, total_tco2e, milestones, kpis
            )

        result = {
            "roadmap_text":   roadmap_text,
            "milestones":     milestones,
            "kpis":           kpis,
            "status":         "AWAITING_APPROVAL",   # HITL gate — not exportable until approved
            "export_ready":   False,
            "org_name":       org_name,
            "agent":          self.AGENT_NAME,
        }

        log.info(
            f"{self.AGENT_NAME} complete. Status: AWAITING_APPROVAL (HITL gate active)",
            extra={"action": "agent_complete",
                   "outputs": {"status": "AWAITING_APPROVAL"}}
        )
        return result

    @staticmethod
    def _fallback_roadmap(
        org_name: str,
        total_tco2e: float,
        milestones: list,
        kpis: dict,
    ) -> str:
        """Return a structured text fallback when LLM is unavailable."""
        lines = [
            f"ESG DECARBONIZATION ROADMAP — {org_name}",
            "=" * 60,
            f"Baseline Emissions: {format_tco2e(total_tco2e)}",
            "",
        ]
        for m in milestones:
            lines.append(f"{m['phase']}:")
            for action in m["actions"]:
                lines.append(f"  • {action}")
            lines.append(
                f"  Expected reduction: {format_tco2e(m['tco2e_reduction'])} | "
                f"Investment: {format_currency(m['investment'])}"
            )
            lines.append("")
        lines.append(
            "DISCLAIMER: This AI-generated roadmap requires validation by a "
            "certified sustainability professional before regulatory use."
        )
        return "\n".join(lines)
