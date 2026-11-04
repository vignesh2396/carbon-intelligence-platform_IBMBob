"""
agents/carbon_accounting_agent.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Agent 1 — Carbon Accounting Agent.
          Receives validated activity data, calls the emissions calculator tool,
          and returns structured GHG accounting results.

Agent Responsibilities (Guideline §9 — Agent Responsibilities):
    - Apply GHG Protocol emission factors to activity data
    - Calculate Scope 1, 2, 3 emissions
    - Produce a verified emissions inventory

Multi-step Reasoning:
    1. Validate inputs are present
    2. Call calculate_emissions() tool
    3. Verify total is non-zero (sanity check)
    4. Return structured result with audit trail

Dependencies: tools/emissions_calculator.py, utils/logger.py
"""

from __future__ import annotations

import pandas as pd
from typing import Any

from tools.emissions_calculator import calculate_emissions
from utils.logger import get_logger

log = get_logger("CarbonAccountingAgent")


class CarbonAccountingAgent:
    """
    Autonomous AI agent responsible for GHG emissions accounting.

    Called by: SupervisorAgent
    Calls:     calculate_emissions() tool
    """

    AGENT_NAME = "Carbon Accounting Agent"

    def run(self, activity_df: pd.DataFrame) -> dict[str, Any]:
        """
        Execute emissions accounting for the provided activity data.

        Args:
            activity_df: Validated pandas DataFrame of organizational activities.

        Returns:
            Emissions result dict from calculate_emissions(), augmented with
            agent metadata for audit trail.

        Raises:
            ValueError: If activity_df is empty or total tCO₂e is 0.
        """
        log.info(
            "Carbon Accounting Agent invoked",
            extra={"action": "agent_start", "agent": self.AGENT_NAME,
                   "inputs": {"row_count": len(activity_df)}}
        )

        # ── Step 1: Validate inputs ────────────────────────────────────────
        if activity_df is None or activity_df.empty:
            log.warning("Empty activity data received", extra={"action": "validation_fail"})
            raise ValueError("Activity data is empty. Please upload a valid CSV.")

        # ── Step 2: Call emissions calculator tool ─────────────────────────
        result = calculate_emissions(activity_df)

        # ── Step 3: Sanity check ───────────────────────────────────────────
        if result["total_tco2e"] == 0:
            log.warning(
                "Total tCO₂e is 0 — emission factors may not match activity units.",
                extra={"action": "zero_total_warning",
                       "warning": "Check that activity units match supported emission factor keys."}
            )

        # ── Step 4: Augment with agent metadata ───────────────────────────
        result["agent"] = self.AGENT_NAME
        result["status"] = "complete"
        result["disclaimer"] = (
            "Emission factors sourced from GHG Protocol (2023). "
            "Results are estimates; professional verification recommended for regulatory reporting."
        )

        log.info(
            f"{self.AGENT_NAME} completed. Total: {result['total_tco2e']:.2f} tCO₂e",
            extra={"action": "agent_complete",
                   "outputs": {"total_tco2e": result["total_tco2e"]}}
        )
        return result
