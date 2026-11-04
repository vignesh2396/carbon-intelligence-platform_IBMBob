"""
data/db_setup.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Creates and initializes the SQLite database schema.
          Run once at application startup (idempotent — safe to re-run).

Schema implements the ER diagram from Phase 5 of the SDLC design document.

Dependencies: sqlite3 (stdlib), os
"""

import sqlite3
import os
from utils.logger import get_logger

log = get_logger("DatabaseSetup")

DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/carbon_db.sqlite")


CREATE_STATEMENTS = [
    # ── Organization ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS organization (
        org_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        org_name        TEXT    NOT NULL,
        industry        TEXT,
        reporting_year  TEXT    NOT NULL,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Emission Record ───────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS emission_record (
        record_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id              INTEGER NOT NULL REFERENCES organization(org_id),
        scope               TEXT    NOT NULL CHECK(scope IN ('Scope 1','Scope 2','Scope 3')),
        category            TEXT    NOT NULL,
        activity_description TEXT,
        quantity            REAL    NOT NULL CHECK(quantity > 0),
        unit                TEXT    NOT NULL,
        emission_factor     REAL    NOT NULL,
        tco2e               REAL    NOT NULL,
        recorded_at         DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Hotspot ─────────────────────���─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS hotspot (
        hotspot_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id          INTEGER NOT NULL REFERENCES organization(org_id),
        activity        TEXT    NOT NULL,
        business_unit   TEXT,
        tco2e           REAL    NOT NULL,
        pct_contribution REAL   NOT NULL,
        rank            INTEGER NOT NULL
    )
    """,

    # ── Reduction Strategy ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS reduction_strategy (
        strategy_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        hotspot_id                  INTEGER NOT NULL REFERENCES hotspot(hotspot_id),
        strategy_name               TEXT    NOT NULL,
        description                 TEXT,
        estimated_reduction_tco2e   REAL,
        estimated_cost_usd          REAL,
        feasibility_score           REAL    CHECK(feasibility_score BETWEEN 0 AND 1),
        timeframe                   TEXT,
        sources                     TEXT
    )
    """,

    # ── Scenario ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS scenario (
        scenario_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id                  INTEGER NOT NULL REFERENCES organization(org_id),
        scenario_name           TEXT    NOT NULL,
        scenario_type           TEXT    NOT NULL,
        strategy_ids_applied    TEXT,
        projected_tco2e_yr1     REAL,
        projected_tco2e_yr3     REAL,
        total_reduction_pct     REAL
    )
    """,

    # ── ESG Roadmap ───────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS esg_roadmap (
        roadmap_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id          INTEGER NOT NULL REFERENCES organization(org_id),
        status          TEXT    NOT NULL DEFAULT 'DRAFT'
                        CHECK(status IN ('DRAFT','AWAITING_APPROVAL','APPROVED','REJECTED')),
        milestones      TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at     DATETIME,
        approved_by     TEXT
    )
    """,

    # ── Indexes ───────────────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_emission_org_scope ON emission_record(org_id, scope)",
    "CREATE INDEX IF NOT EXISTS idx_hotspot_rank ON hotspot(org_id, rank)",
    "CREATE INDEX IF NOT EXISTS idx_strategy_feasibility ON reduction_strategy(hotspot_id, feasibility_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_roadmap_status ON esg_roadmap(org_id, status)",
]


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Initialize the SQLite database, creating all tables and indexes.
    Safe to call on every application startup (all statements use IF NOT EXISTS).

    Returns an open sqlite3.Connection for use by the calling agent.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # write-ahead log for concurrency
    conn.execute("PRAGMA foreign_keys=ON")    # enforce FK constraints

    with conn:
        for stmt in CREATE_STATEMENTS:
            conn.execute(stmt)

    log.info(
        "Database initialized",
        extra={"action": "db_init", "db_path": db_path}
    )
    return conn


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a database connection (row_factory = sqlite3.Row for dict-like access)."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
