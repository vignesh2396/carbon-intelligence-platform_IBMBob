"""
agents/reduction_strategy_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 3 — Reduction Strategy Agent.
          Uses RAG + LLM to generate targeted decarbonization strategies
          for each identified carbon hotspot.

Agentic AI Requirements fulfilled (Guideline §4):
    ✓ Tool calling: RAG retriever tool
    ✓ RAG: Knowledge grounded in GHG Protocol / IPCC documents
    ✓ Explainability: Sources shown for every strategy
    ✓ Confidence indicators: Shown for each recommendation

Multi-step reasoning:
    1. For each hotspot, query the RAG knowledge base
    2. Build a context-grounded prompt
    3. Call LLM to synthesize 3 specific strategies
    4. Return strategies with sources and confidence

Dependencies: rag/retriever.py, langchain_google_genai
"""

from __future__ import annotations

import os
import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from rag.retriever import retrieve_reduction_strategies, format_rag_context
from utils.logger import get_logger

log = get_logger("ReductionStrategyAgent")


SYSTEM_PROMPT = """You are an expert sustainability consultant and carbon reduction specialist.
Your role is to recommend practical, evidence-based decarbonization strategies.

RULES:
1. Base every recommendation on the provided knowledge base context.
2. Each strategy must include: name, description, estimated_reduction_tco2e, 
   estimated_cost_usd, feasibility_score (0.0-1.0), timeframe.
3. Provide EXACTLY 3 strategies.
4. Return ONLY valid JSON — no markdown, no extra text.
5. If knowledge base context is limited, say so in the strategy description.
6. Do NOT claim certainty — use language like "estimated", "typically", "approximately".

Responsible AI: Always recommend human expert review for significant capital decisions.
"""

STRATEGY_PROMPT_TEMPLATE = """
Based on the following knowledge base context, recommend 3 specific carbon reduction strategies
for this emission hotspot:

HOTSPOT: {hotspot_description}
ANNUAL EMISSIONS: {tco2e:.2f} tCO₂e
SCOPE: {scope}
BUSINESS UNIT: {business_unit}

KNOWLEDGE BASE CONTEXT:
{rag_context}

Return a JSON array with exactly 3 strategy objects:
[
  {{
    "strategy_name": "string",
    "description": "string",
    "estimated_reduction_tco2e": number,
    "estimated_cost_usd": number,
    "feasibility_score": number (0.0 to 1.0),
    "timeframe": "string (e.g. '1 year', '2-3 years')",
    "sources": "string (cite the knowledge base sources used)"
  }}
]
"""


class ReductionStrategyAgent:
    """
    Agent 3: Generates RAG-grounded reduction strategies for each hotspot.

    Called by: SupervisorAgent
    Calls:     RAG retriever tool, Gemini LLM
    """

    AGENT_NAME = "Reduction Strategy Agent"

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set. Check your .env file.")
        model_name = os.getenv("LLM_MODEL", "gemini-1.5-pro")
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            google_api_key=api_key,
        )

    def run(
        self,
        analysis_result: dict[str, Any],
        top_n_hotspots: int = 3,
    ) -> dict[str, Any]:
        """
        Generate reduction strategies for the top N hotspots.

        Args:
            analysis_result: Output from EmissionsAnalysisAgent.run()
            top_n_hotspots:  Number of hotspots to generate strategies for (default 3)

        Returns:
            {
                "strategies_by_hotspot": dict[hotspot_activity → list[strategy_dicts]],
                "all_strategies":        flat list of all strategy dicts,
                "rag_sources_used":      list[str],
                "agent":                 str,
            }
        """
        log.info(
            f"{self.AGENT_NAME} invoked for {top_n_hotspots} hotspots",
            extra={"action": "agent_start", "agent": self.AGENT_NAME}
        )

        hotspots = analysis_result.get("hotspots", [])[:top_n_hotspots]
        strategies_by_hotspot: dict[str, list[dict]] = {}
        all_strategies: list[dict] = []
        all_sources: set[str] = set()

        for hotspot in hotspots:
            activity    = hotspot["activity"]
            tco2e       = hotspot["tco2e"]
            scope       = hotspot["scope"]
            business_unit = hotspot.get("business_unit", "N/A")

            # ── Step 1: RAG Retrieval ──────────────────────────────────────
            rag_chunks = retrieve_reduction_strategies(
                f"{activity} ({scope}): carbon reduction"
            )
            rag_context = format_rag_context(rag_chunks)
            sources = [c["source"] for c in rag_chunks]
            all_sources.update(sources)

            # Confidence indicator for explainability
            has_high_confidence = any(c["confidence"] == "High" for c in rag_chunks)
            confidence_note = "" if has_high_confidence else (
                "⚠️ Low RAG confidence for this hotspot. "
                "Strategies are LLM-generated without strong knowledge base grounding. "
                "Human expert review is strongly recommended."
            )

            # ── Step 2: LLM Strategy Generation ───────────────────────────
            prompt = STRATEGY_PROMPT_TEMPLATE.format(
                hotspot_description=activity,
                tco2e=tco2e,
                scope=scope,
                business_unit=business_unit,
                rag_context=rag_context,
            )

            try:
                response = self._llm.invoke([
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ])
                raw_text = response.content.strip()

                # Strip markdown code fences if present
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]

                strategies = json.loads(raw_text)

                # Annotate each strategy with hotspot info + confidence
                for s in strategies:
                    s["hotspot_activity"]  = activity
                    s["hotspot_scope"]     = scope
                    s["hotspot_tco2e"]     = tco2e
                    s["confidence_note"]   = confidence_note
                    s["rag_sources"]       = sources

            except json.JSONDecodeError as e:
                log.warning(
                    f"LLM returned non-JSON for '{activity}': {e}",
                    extra={"action": "json_parse_error", "warning": str(e)}
                )
                # Graceful fallback strategy
                strategies = [self._fallback_strategy(hotspot, confidence_note, sources)]
            except Exception as e:
                log.warning(
                    f"LLM call failed for '{activity}': {e}",
                    extra={"action": "llm_error", "warning": str(e)}
                )
                strategies = [self._fallback_strategy(hotspot, confidence_note, sources)]

            strategies_by_hotspot[activity] = strategies
            all_strategies.extend(strategies)

        log.info(
            f"{self.AGENT_NAME} complete. Generated {len(all_strategies)} strategies "
            f"across {len(strategies_by_hotspot)} hotspots.",
            extra={"action": "agent_complete",
                   "outputs": {"strategy_count": len(all_strategies)}}
        )

        return {
            "strategies_by_hotspot": strategies_by_hotspot,
            "all_strategies":        all_strategies,
            "rag_sources_used":      sorted(all_sources),
            "agent":                 self.AGENT_NAME,
        }

    @staticmethod
    def _fallback_strategy(
        hotspot: dict,
        confidence_note: str,
        sources: list[str]
    ) -> dict:
        """Return a safe generic fallback when LLM is unavailable."""
        return {
            "strategy_name":              f"Generic reduction — {hotspot['category']}",
            "description":                (
                f"Implement industry-standard best practices for {hotspot['category']} "
                f"emission reduction. Consult a certified sustainability professional."
            ),
            "estimated_reduction_tco2e":  round(hotspot["tco2e"] * 0.20, 2),
            "estimated_cost_usd":         25_000.0,
            "feasibility_score":          0.5,
            "timeframe":                  "2-3 years",
            "sources":                    ", ".join(sources) or "GHG Protocol",
            "hotspot_activity":           hotspot["activity"],
            "hotspot_scope":              hotspot["scope"],
            "hotspot_tco2e":              hotspot["tco2e"],
            "confidence_note":            confidence_note or "⚠️ LLM unavailable — fallback strategy.",
            "rag_sources":                sources,
        }
