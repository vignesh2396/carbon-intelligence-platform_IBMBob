"""
tools/emissions_calculator.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Tool 1 — GHG Protocol-based emissions calculator.
          Converts organizational activity data into tCO₂e values using
          authoritative emission factors. Called by the Carbon Accounting Agent.

Design:   Pure function — no side effects, fully testable.
          Agents call calculate_emissions() and receive a structured dict.

Dependencies: pandas, utils/helpers.py
"""

from __future__ import annotations

import pandas as pd
from typing import Any

from utils.helpers import (
    GHG_EMISSION_FACTORS,
    normalise_unit,
    kg_to_tonne,
    pct,
)
from utils.logger import get_logger

log = get_logger("EmissionsCalculatorTool")

# ── Activity → Emission Factor Key Mapping ───────────────────────────────────
# Maps CSV 'category' values to emission factor keys in GHG_EMISSION_FACTORS.
CATEGORY_FACTOR_MAP: dict[str, str] = {
    "Purchased Electricity": "electricity_kwh",
    "Stationary Combustion":  "natural_gas_kwh",   # default; unit-refined below
    "Mobile Combustion":      "diesel_litre",       # default; unit-refined below
    "Business Travel":        "air_travel_short_pkm",
    "Waste":                  "landfill_waste_tonne",
    "Purchased Goods & Services": "procurement_usd",
}

# ── Unit-Aware Refinement ─────────────────────────────────────────────────────
UNIT_FACTOR_OVERRIDE: dict[str, str] = {
    "litre":  "diesel_litre",
    "pkm":    "air_travel_short_pkm",
    "tonne":  "landfill_waste_tonne",
    "USD":    "procurement_usd",
    "kWh":    "electricity_kwh",
    "MWh":    "electricity_mwh",
}


def _resolve_factor_key(category: str, unit: str) -> tuple[str, float]:
    """
    Resolve the correct emission factor key for a given activity category and unit.
    Returns (factor_key, factor_value_kg_per_unit).
    """
    canonical_unit = normalise_unit(unit)

    # Try unit-based override first (more specific)
    factor_key = UNIT_FACTOR_OVERRIDE.get(canonical_unit)
    if not factor_key:
        factor_key = CATEGORY_FACTOR_MAP.get(category, "electricity_kwh")

    factor_entry = GHG_EMISSION_FACTORS.get(factor_key, {})
    factor_value = factor_entry.get("factor", 0.0)

    return factor_key, factor_value


def calculate_emissions(activity_df: pd.DataFrame) -> dict[str, Any]:
    """
    Calculate organizational GHG emissions from activity data.

    Args:
        activity_df: Validated pandas DataFrame with columns:
                     [activity, category, scope, quantity, unit, business_unit]

    Returns:
        {
            "scope1_tco2e":   float,
            "scope2_tco2e":   float,
            "scope3_tco2e":   float,
            "total_tco2e":    float,
            "breakdown":      list[dict],    # per-activity detail
            "scope_summary":  dict[str,float], # {scope: tco2e}
            "bu_summary":     dict[str,float], # {business_unit: tco2e}
        }
    """
    log.info("Starting emissions calculation", extra={"action": "calculate_start",
             "row_count": len(activity_df)})

    breakdown: list[dict] = []

    for _, row in activity_df.iterrows():
        category  = str(row.get("category", "")).strip()
        scope     = str(row.get("scope", "")).strip()
        quantity  = float(row.get("quantity", 0))
        unit      = str(row.get("unit", "")).strip()
        activity  = str(row.get("activity", "")).strip()
        bu        = str(row.get("business_unit", "Unknown")).strip()

        factor_key, factor_kg = _resolve_factor_key(category, unit)

        # Convert kWh MWh: MWh factors already per-MWh, no conversion needed
        tco2e = kg_to_tonne(quantity * factor_kg)

        breakdown.append({
            "activity":      activity,
            "category":      category,
            "scope":         scope,
            "business_unit": bu,
            "quantity":      quantity,
            "unit":          unit,
            "factor_key":    factor_key,
            "factor_kg_per_unit": factor_kg,
            "tco2e":         round(tco2e, 4),
        })

    # ── Aggregations ─────────────────────────────────────────────────────────
    scope1 = sum(r["tco2e"] for r in breakdown if r["scope"] == "Scope 1")
    scope2 = sum(r["tco2e"] for r in breakdown if r["scope"] == "Scope 2")
    scope3 = sum(r["tco2e"] for r in breakdown if r["scope"] == "Scope 3")
    total  = scope1 + scope2 + scope3

    scope_summary = {"Scope 1": round(scope1, 2),
                     "Scope 2": round(scope2, 2),
                     "Scope 3": round(scope3, 2)}

    bu_summary: dict[str, float] = {}
    for r in breakdown:
        bu_summary[r["business_unit"]] = round(
            bu_summary.get(r["business_unit"], 0) + r["tco2e"], 2
        )

    result = {
        "scope1_tco2e":  round(scope1, 2),
        "scope2_tco2e":  round(scope2, 2),
        "scope3_tco2e":  round(scope3, 2),
        "total_tco2e":   round(total, 2),
        "breakdown":     breakdown,
        "scope_summary": scope_summary,
        "bu_summary":    bu_summary,
    }

    log.info(
        f"Emissions calculated: {total:.2f} tCO₂e",
        extra={
            "action":  "calculate_complete",
            "outputs": {"total_tco2e": total, "scope_summary": scope_summary}
        }
    )
    return result
