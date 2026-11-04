"""
utils/helpers.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Unit conversion utilities, number formatting helpers, and
          shared constants used across the agent pipeline.

Dependencies: None (standard library only)
"""

from __future__ import annotations

# ── Emission factor unit → kg CO₂e per unit ──────────────────────────────────
# Source: GHG Protocol / IPCC AR6 (simplified representative values for prototype)
# Real deployment should use the latest official GHG Protocol emission factor database.

GHG_EMISSION_FACTORS: dict[str, dict[str, float]] = {
    # Scope 1 — Direct combustion (kg CO₂e per litre unless noted)
    "natural_gas_kwh":       {"factor": 0.2025,  "unit": "kWh",    "scope": "Scope 1"},
    "diesel_litre":          {"factor": 2.6826,  "unit": "litre",  "scope": "Scope 1"},
    "petrol_litre":          {"factor": 2.3153,  "unit": "litre",  "scope": "Scope 1"},
    "lpg_litre":             {"factor": 1.5448,  "unit": "litre",  "scope": "Scope 1"},
    "coal_tonne":            {"factor": 2533.0,  "unit": "tonne",  "scope": "Scope 1"},

    # Scope 2 — Purchased electricity (kg CO₂e per kWh — global average grid)
    "electricity_kwh":       {"factor": 0.4330,  "unit": "kWh",    "scope": "Scope 2"},
    "electricity_mwh":       {"factor": 433.0,   "unit": "MWh",    "scope": "Scope 2"},

    # Scope 3 — Business travel (kg CO₂e per passenger-km)
    "air_travel_short_pkm":  {"factor": 0.2553,  "unit": "pkm",    "scope": "Scope 3"},
    "air_travel_long_pkm":   {"factor": 0.1950,  "unit": "pkm",    "scope": "Scope 3"},
    "rail_travel_pkm":       {"factor": 0.0410,  "unit": "pkm",    "scope": "Scope 3"},
    "road_travel_pkm":       {"factor": 0.1710,  "unit": "pkm",    "scope": "Scope 3"},

    # Scope 3 — Waste (kg CO₂e per tonne)
    "landfill_waste_tonne":  {"factor": 467.0,   "unit": "tonne",  "scope": "Scope 3"},
    "recycled_waste_tonne":  {"factor": 21.0,    "unit": "tonne",  "scope": "Scope 3"},

    # Scope 3 — Purchased goods & services (kg CO₂e per USD spend — EEIO average)
    "procurement_usd":       {"factor": 0.32,    "unit": "USD",    "scope": "Scope 3"},
}

# ── Unit Normalisation ────────────────────────────────────────────────────────
UNIT_ALIASES: dict[str, str] = {
    "kwh": "kWh",
    "mwh": "MWh",
    "liter": "litre",
    "liters": "litre",
    "litres": "litre",
    "l": "litre",
    "kg": "kg",
    "t": "tonne",
    "ton": "tonne",
    "tons": "tonne",
    "tonnes": "tonne",
    "km": "pkm",
    "passenger-km": "pkm",
    "passenger_km": "pkm",
    "pkm": "pkm",
    "tonne-km": "tkm",
    "$": "USD",
    "usd": "USD",
}


def normalise_unit(unit: str) -> str:
    """Normalise user-supplied unit string to canonical form."""
    return UNIT_ALIASES.get(unit.strip().lower(), unit.strip())


def format_tco2e(value: float) -> str:
    """Format a tCO₂e value with appropriate precision and unit label."""
    if value >= 1000:
        return f"{value / 1000:,.2f} ktCO₂e"
    return f"{value:,.2f} tCO₂e"


def format_currency(value: float, currency: str = "USD") -> str:
    """Format a monetary value."""
    return f"{currency} {value:,.0f}"


def kg_to_tonne(kg: float) -> float:
    """Convert kilograms CO₂e to metric tonnes CO₂e."""
    return kg / 1000.0


def pct(part: float, total: float) -> float:
    """Safe percentage calculation."""
    return round((part / total) * 100, 2) if total else 0.0
