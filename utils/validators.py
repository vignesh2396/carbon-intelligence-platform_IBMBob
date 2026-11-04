"""
utils/validators.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Input validation for emissions data uploaded by users.
          Prevents malformed data from propagating into the agent pipeline.
          Returns structured validation results suitable for UI display.

Dependencies: pandas, pydantic
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, field_validator
from typing import Optional


# ── Expected CSV Schema ───────────────────────────────────────────────────────
REQUIRED_COLUMNS = {"activity", "category", "scope", "quantity", "unit"}

VALID_SCOPES = {"Scope 1", "Scope 2", "Scope 3"}

# All forms accepted by the UNIT_ALIASES map in utils/helpers.py,
# plus their canonical post-normalisation counterparts.
# Keeping this in sync with helpers.UNIT_ALIASES prevents false warnings.
VALID_UNITS = {
    # Electricity
    "kWh", "MWh", "kwh", "mwh",
    # Liquid fuel
    "litre", "litres", "liter", "liters", "l",
    # Mass
    "kg", "tonne", "tonnes", "ton", "tons", "t",
    # Distance / travel
    "km", "pkm", "passenger-km", "passenger_km",
    # Freight
    "tonne-km", "tkm",
    # Currency (procurement)
    "USD", "usd", "$",
    # Volume
    "m3",
}


class ValidationResult(BaseModel):
    """Structured result returned after CSV validation."""
    is_valid: bool
    errors:   list[str]
    warnings: list[str]
    clean_df: Optional[pd.DataFrame] = None

    class Config:
        arbitrary_types_allowed = True


def validate_emissions_csv(df: pd.DataFrame) -> ValidationResult:
    """
    Validate an emissions activity DataFrame.

    Rules enforced:
    - All required columns must be present
    - 'quantity' must be numeric and positive
    - 'scope' must be one of {Scope 1, Scope 2, Scope 3}
    - No entirely empty rows

    Returns a ValidationResult with is_valid flag, errors list, and clean DataFrame.
    """
    errors: list[str]   = []
    warnings: list[str] = []

    # Rule 1: Required columns
    missing_cols = REQUIRED_COLUMNS - set(df.columns.str.strip().str.lower())
    if missing_cols:
        errors.append(
            f"Missing required column(s): {', '.join(sorted(missing_cols))}. "
            f"Expected: {', '.join(sorted(REQUIRED_COLUMNS))}"
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # Normalise column names
    df.columns = df.columns.str.strip().str.lower()

    # Rule 2: Remove completely empty rows (with warning)
    empty_rows = df[df.isnull().all(axis=1)]
    if not empty_rows.empty:
        warnings.append(f"{len(empty_rows)} empty row(s) were removed.")
        df = df.dropna(how="all").reset_index(drop=True)

    # Rule 3: Quantity must be numeric
    non_numeric = pd.to_numeric(df["quantity"], errors="coerce").isna()
    if non_numeric.any():
        bad_rows = df.index[non_numeric].tolist()
        errors.append(
            f"'quantity' contains non-numeric values in row(s): {[r+2 for r in bad_rows]} "
            f"(row 1 = header)"
        )

    # Rule 4: Quantity must be positive
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    negative_rows = df[df["quantity"] <= 0]
    if not negative_rows.empty:
        errors.append(
            f"'quantity' must be a positive number. "
            f"Negative or zero values found in row(s): {(negative_rows.index + 2).tolist()}"
        )

    # Rule 5: Valid scopes
    invalid_scopes = df[~df["scope"].isin(VALID_SCOPES)]
    if not invalid_scopes.empty:
        unique_bad = invalid_scopes["scope"].unique().tolist()
        errors.append(
            f"Invalid scope value(s): {unique_bad}. "
            f"Allowed values: {sorted(VALID_SCOPES)}"
        )

    # Rule 6: Unit warnings (not blocking — unknown units may still be valid)
    unknown_units = df[~df["unit"].isin(VALID_UNITS)]["unit"].unique().tolist()
    if unknown_units:
        warnings.append(
            f"Unrecognised unit(s): {unknown_units}. "
            f"Emission factors may not be available for these units."
        )

    is_valid = len(errors) == 0
    clean_df = df if is_valid else None
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        clean_df=clean_df
    )
