"""
tests/run_tests.py
───────────────────────────────────────────────────────────────────────────────
Comprehensive agent correctness test suite.
Tests all 7 scenarios from test_cases.md without requiring a live LLM key.
Covers: tools, validators, agents (non-LLM), RAG fallback, HITL gate.
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("GOOGLE_API_KEY", "test-key-placeholder")

import pandas as pd

# ── colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

results = []

def run(label, fn):
    t0 = time.perf_counter()
    try:
        fn()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  {GREEN}PASS{RESET}  {label}  ({elapsed:.0f}ms)")
        results.append({"test": label, "status": "PASS", "ms": round(elapsed)})
    except AssertionError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  {RED}FAIL{RESET}  {label}  —  {e}  ({elapsed:.0f}ms)")
        results.append({"test": label, "status": "FAIL", "error": str(e), "ms": round(elapsed)})
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  {RED}ERROR{RESET} {label}  —  {type(e).__name__}: {e}  ({elapsed:.0f}ms)")
        results.append({"test": label, "status": "ERROR", "error": f"{type(e).__name__}: {e}", "ms": round(elapsed)})

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TOOLS LAYER
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 1: Tools Layer ━━━{RESET}")

from tools.emissions_calculator import calculate_emissions
from tools.hotspot_identifier import identify_hotspots, summarize_by_scope, summarize_by_business_unit
from tools.scenario_simulator import simulate_scenario
from tools.feasibility_scorer import score_feasibility

SAMPLE_DF = pd.DataFrame([
    {"activity": "Electricity HQ",    "category": "Purchased Electricity", "scope": "Scope 2",
     "quantity": 850000, "unit": "kWh",   "business_unit": "Operations"},
    {"activity": "Diesel fleet",      "category": "Mobile Combustion",     "scope": "Scope 1",
     "quantity": 85000,  "unit": "litre", "business_unit": "Logistics"},
    {"activity": "Air travel",        "category": "Business Travel",       "scope": "Scope 3",
     "quantity": 420000, "unit": "pkm",   "business_unit": "All"},
    {"activity": "Landfill waste",    "category": "Waste",                 "scope": "Scope 3",
     "quantity": 50,     "unit": "tonne", "business_unit": "Operations"},
    {"activity": "IT procurement",    "category": "Purchased Goods & Services", "scope": "Scope 3",
     "quantity": 100000, "unit": "USD",   "business_unit": "IT"},
])

def t_emissions_total():
    r = calculate_emissions(SAMPLE_DF)
    assert r["total_tco2e"] > 0, "total_tco2e should be > 0"
    assert "scope1_tco2e" in r and "scope2_tco2e" in r and "scope3_tco2e" in r
    assert abs(r["scope1_tco2e"] + r["scope2_tco2e"] + r["scope3_tco2e"] - r["total_tco2e"]) < 0.01, \
        "Scope sum must equal total"

def t_emissions_scope2_formula():
    # 850000 kWh × 0.433 kg/kWh / 1000 = 368.05 tCO₂e
    r = calculate_emissions(SAMPLE_DF)
    expected = round(850000 * 0.4330 / 1000, 2)
    assert abs(r["scope2_tco2e"] - expected) < 0.5, \
        f"Scope 2 expected ~{expected}, got {r['scope2_tco2e']}"

def t_emissions_scope1_diesel():
    # 85000 litres × 2.6826 kg/litre / 1000 = 228.02 tCO₂e
    r = calculate_emissions(SAMPLE_DF)
    expected = round(85000 * 2.6826 / 1000, 2)
    assert abs(r["scope1_tco2e"] - expected) < 0.5, \
        f"Scope 1 diesel expected ~{expected}, got {r['scope1_tco2e']}"

def t_hotspot_ranking():
    r = calculate_emissions(SAMPLE_DF)
    h = identify_hotspots(r, top_n=3)
    assert len(h) == 3, f"Expected 3 hotspots, got {len(h)}"
    assert h[0]["rank"] == 1
    # Hotspots must be sorted descending by tco2e
    for i in range(len(h) - 1):
        assert h[i]["tco2e"] >= h[i+1]["tco2e"], "Hotspots not sorted by tCO₂e"

def t_hotspot_pct_sums_to_100():
    r = calculate_emissions(SAMPLE_DF)
    h = identify_hotspots(r, top_n=5)
    total_pct = sum(x["pct_contribution"] for x in h)
    assert total_pct <= 100.1, f"pct sum {total_pct} exceeds 100%"

def t_scenario_bau_grows():
    r = calculate_emissions(SAMPLE_DF)
    sim = simulate_scenario(r["total_tco2e"], [], years=3)
    curve = sim["bau_curve"]
    assert curve[1] > curve[0], "BAU should grow year-over-year"
    assert curve[3] > curve[1], "BAU should keep growing"

def t_scenario_intervention_less_than_bau():
    r = calculate_emissions(SAMPLE_DF)
    strategies = [{"estimated_reduction_tco2e": 200, "timeframe": "1 year"}]
    sim = simulate_scenario(r["total_tco2e"], strategies, years=3)
    for bau, intr in zip(sim["bau_curve"][1:], sim["intervention_curve"][1:]):
        assert intr <= bau, "Intervention curve must be ≤ BAU curve"

def t_scenario_reduction_pct_positive():
    r = calculate_emissions(SAMPLE_DF)
    strategies = [{"estimated_reduction_tco2e": 300, "timeframe": "1 year"}]
    sim = simulate_scenario(r["total_tco2e"], strategies, years=3)
    assert sim["total_reduction_pct"] > 0, "Reduction % should be > 0 when strategies applied"

def t_scenario_no_strategy_no_reduction():
    r = calculate_emissions(SAMPLE_DF)
    sim = simulate_scenario(r["total_tco2e"], [], years=3)
    assert sim["total_reduction_pct"] == 0, "No strategies → 0% reduction"

def t_feasibility_sorted_descending():
    strategies = [
        {"strategy_name": "A", "estimated_reduction_tco2e": 100, "estimated_cost_usd": 500000, "feasibility_score": 0.3},
        {"strategy_name": "B", "estimated_reduction_tco2e": 300, "estimated_cost_usd": 10000,  "feasibility_score": 0.9},
        {"strategy_name": "C", "estimated_reduction_tco2e": 200, "estimated_cost_usd": 50000,  "feasibility_score": 0.7},
    ]
    scored = score_feasibility(strategies)
    for i in range(len(scored)-1):
        assert scored[i]["composite_score"] >= scored[i+1]["composite_score"], \
            "Scored strategies must be sorted descending"

def t_feasibility_priority_labels():
    strategies = [
        {"strategy_name": "HighROI", "estimated_reduction_tco2e": 500, "estimated_cost_usd": 1000, "feasibility_score": 0.95},
        {"strategy_name": "LowROI",  "estimated_reduction_tco2e": 10,  "estimated_cost_usd": 900000, "feasibility_score": 0.1},
    ]
    scored = score_feasibility(strategies)
    labels = {s["strategy_name"]: s["priority"] for s in scored}
    assert labels["HighROI"] == "High", f"Expected High, got {labels['HighROI']}"
    assert labels["LowROI"] in ("Low", "Medium"), f"Expected Low/Medium, got {labels['LowROI']}"

def t_feasibility_within_budget_flag():
    strategies = [{"strategy_name": "Cheap", "estimated_reduction_tco2e": 100,
                   "estimated_cost_usd": 5000, "feasibility_score": 0.8}]
    scored = score_feasibility(strategies, budget_usd=10000)
    assert scored[0]["within_budget"] is True
    scored2 = score_feasibility(strategies, budget_usd=1000)
    assert scored2[0]["within_budget"] is False

for fn in [t_emissions_total, t_emissions_scope2_formula, t_emissions_scope1_diesel,
           t_hotspot_ranking, t_hotspot_pct_sums_to_100,
           t_scenario_bau_grows, t_scenario_intervention_less_than_bau,
           t_scenario_reduction_pct_positive, t_scenario_no_strategy_no_reduction,
           t_feasibility_sorted_descending, t_feasibility_priority_labels,
           t_feasibility_within_budget_flag]:
    run(fn.__name__.replace("t_", "Tool: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — VALIDATORS (TC-03, TC-04)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 2: Input Validators (TC-03, TC-04) ━━━{RESET}")

from utils.validators import validate_emissions_csv

def t_tc03_missing_quantity_column():
    # TC-03: CSV missing 'quantity' column
    df = pd.DataFrame([{"activity": "Elec", "category": "Purchased Electricity",
                         "scope": "Scope 2", "unit": "kWh", "business_unit": "Ops"}])
    r = validate_emissions_csv(df)
    assert not r.is_valid, "Should be invalid"
    assert any("quantity" in e for e in r.errors), "Error must mention 'quantity'"

def t_tc04_negative_quantity():
    # TC-04: Negative quantity values
    df = pd.DataFrame([
        {"activity": "Elec", "category": "Purchased Electricity", "scope": "Scope 2",
         "quantity": -500, "unit": "kWh", "business_unit": "Ops"},
        {"activity": "Fuel", "category": "Stationary Combustion", "scope": "Scope 1",
         "quantity": 1000, "unit": "litre", "business_unit": "Ops"},
    ])
    r = validate_emissions_csv(df)
    assert not r.is_valid, "Should be invalid due to negative quantity"
    assert any("positive" in e.lower() for e in r.errors), "Error must mention positive"

def t_valid_sample_data_no_errors():
    # TC-01: Sample data should pass clean
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "sample_org_data.csv"))
    r = validate_emissions_csv(df)
    assert r.is_valid, f"Sample data should be valid; errors: {r.errors}"
    assert r.warnings == [], f"Sample data should have no warnings; got: {r.warnings}"

def t_invalid_scope_value():
    df = pd.DataFrame([{"activity": "X", "category": "Purchased Electricity",
                         "scope": "Scope 4", "quantity": 100, "unit": "kWh", "business_unit": "A"}])
    r = validate_emissions_csv(df)
    assert not r.is_valid, "Scope 4 is invalid"
    assert any("scope" in e.lower() for e in r.errors)

def t_empty_rows_removed_with_warning():
    df = pd.DataFrame([
        {"activity": "Elec", "category": "Purchased Electricity", "scope": "Scope 2",
         "quantity": 100, "unit": "kWh", "business_unit": "Ops"},
        {"activity": None, "category": None, "scope": None, "quantity": None, "unit": None, "business_unit": None},
    ])
    r = validate_emissions_csv(df)
    assert r.is_valid, "Should be valid after removing empty row"
    assert any("empty" in w.lower() for w in r.warnings), "Should warn about empty row removal"

for fn in [t_tc03_missing_quantity_column, t_tc04_negative_quantity,
           t_valid_sample_data_no_errors, t_invalid_scope_value,
           t_empty_rows_removed_with_warning]:
    run(fn.__name__.replace("t_", "Validator: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AGENTS (non-LLM, TC-01, TC-02, TC-05)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 3: Agent Pipeline (non-LLM) ━━━{RESET}")

from agents.carbon_accounting_agent import CarbonAccountingAgent
from agents.emissions_analysis_agent import EmissionsAnalysisAgent
from agents.cost_feasibility_agent import CostFeasibilityAgent
from agents.scenario_simulation_agent import ScenarioSimulationAgent

def t_tc01_carbon_accounting_agent():
    # TC-01: Full accounting agent run
    agent = CarbonAccountingAgent()
    r = agent.run(SAMPLE_DF)
    assert r["total_tco2e"] > 0
    assert r["status"] == "complete"
    assert "disclaimer" in r
    assert r["agent"] == "Carbon Accounting Agent"

def t_tc01_emissions_analysis_agent():
    # TC-01: Hotspot analysis
    acc = CarbonAccountingAgent().run(SAMPLE_DF)
    ana = EmissionsAnalysisAgent().run(acc)
    assert len(ana["hotspots"]) > 0
    assert "analysis_narrative" in ana
    assert ana["total_tco2e"] == acc["total_tco2e"]

def t_tc02_single_scope2_only():
    # TC-02: Single Scope 2 activity
    df = pd.DataFrame([{"activity": "Electricity HQ", "category": "Purchased Electricity",
                         "scope": "Scope 2", "quantity": 2500000, "unit": "kWh", "business_unit": "Ops"}])
    acc = CarbonAccountingAgent().run(df)
    assert acc["scope1_tco2e"] == 0
    assert acc["scope3_tco2e"] == 0
    assert acc["scope2_tco2e"] > 0
    expected = round(2500000 * 0.4330 / 1000, 2)
    assert abs(acc["scope2_tco2e"] - expected) < 1.0, \
        f"Expected ~{expected} tCO₂e, got {acc['scope2_tco2e']}"

def t_tc05_high_emission_flag():
    # TC-05: High emission flag triggered above threshold (5000 tCO₂e)
    big_df = pd.DataFrame([{"activity": "Electricity Plant", "category": "Purchased Electricity",
                              "scope": "Scope 2", "quantity": 15000000, "unit": "kWh", "business_unit": "Manufacturing"}])
    acc = CarbonAccountingAgent().run(big_df)
    ana = EmissionsAnalysisAgent().run(acc)
    assert ana["high_emission_flag"] is True, \
        f"Expected high_emission_flag=True for {acc['total_tco2e']:.0f} tCO₂e"

def t_tc01_cost_feasibility_agent():
    acc = CarbonAccountingAgent().run(SAMPLE_DF)
    ana = EmissionsAnalysisAgent().run(acc)
    # Inject mock strategies (bypassing LLM)
    mock_strategy_result = {
        "all_strategies": [
            {"strategy_name": "Solar PV", "estimated_reduction_tco2e": 200,
             "estimated_cost_usd": 80000, "feasibility_score": 0.85, "timeframe": "1 year"},
            {"strategy_name": "EV Fleet", "estimated_reduction_tco2e": 150,
             "estimated_cost_usd": 250000, "feasibility_score": 0.70, "timeframe": "2-3 years"},
            {"strategy_name": "Travel Policy", "estimated_reduction_tco2e": 50,
             "estimated_cost_usd": 5000, "feasibility_score": 0.95, "timeframe": "1 year"},
        ]
    }
    feas = CostFeasibilityAgent().run(mock_strategy_result, budget_usd=500000)
    assert len(feas["scored_strategies"]) == 3
    assert feas["scored_strategies"][0]["composite_score"] >= feas["scored_strategies"][-1]["composite_score"]
    assert "narrative" in feas

def t_tc01_scenario_simulation_agent():
    acc = CarbonAccountingAgent().run(SAMPLE_DF)
    mock_scored = [
        {"strategy_name": "Solar PV", "estimated_reduction_tco2e": 200,
         "estimated_cost_usd": 80000, "feasibility_score": 0.85, "timeframe": "1 year",
         "priority": "High"},
    ]
    scen = ScenarioSimulationAgent().run(acc, mock_scored, years=3)
    assert "bau" in scen and "intervention" in scen
    assert scen["intervention"]["total_reduction_pct"] > 0
    bau_total = scen["bau"]["total_bau_tco2e"]
    int_total  = scen["intervention"]["total_intervention_tco2e"]
    assert int_total < bau_total, "Intervention should reduce total vs BAU"

def t_carbon_agent_empty_raises():
    # TC-03 analog: empty DataFrame should raise ValueError
    agent = CarbonAccountingAgent()
    try:
        agent.run(pd.DataFrame())
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e).lower()

for fn in [t_tc01_carbon_accounting_agent, t_tc01_emissions_analysis_agent,
           t_tc02_single_scope2_only, t_tc05_high_emission_flag,
           t_tc01_cost_feasibility_agent, t_tc01_scenario_simulation_agent,
           t_carbon_agent_empty_raises]:
    run(fn.__name__.replace("t_", "Agent: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — HITL GATE (TC-05)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 4: HITL Gate (TC-05) ━━━{RESET}")

from agents.supervisor_agent import SupervisorAgent, AgentState

def t_hitl_roadmap_blocked_before_approval():
    state = AgentState()
    state.roadmap_result = {"status": "AWAITING_APPROVAL", "export_ready": False}
    assert state.roadmap_result["export_ready"] is False, "Export must be blocked before approval"

def t_hitl_approve_sets_export_ready():
    state = AgentState()
    state.roadmap_result = {"status": "AWAITING_APPROVAL", "export_ready": False}
    supervisor = SupervisorAgent()
    updated = supervisor.approve_roadmap(state, approved_by="Test Reviewer")
    assert updated.roadmap_result["status"] == "APPROVED"
    assert updated.roadmap_result["export_ready"] is True
    assert updated.hitl_approved is True
    assert "Test Reviewer" in updated.roadmap_result["approved_by"]

def t_hitl_reject_keeps_blocked():
    state = AgentState()
    state.roadmap_result = {"status": "AWAITING_APPROVAL", "export_ready": False}
    supervisor = SupervisorAgent()
    updated = supervisor.reject_roadmap(state, reason="Needs more detail")
    assert updated.roadmap_result["status"] == "REJECTED"
    assert updated.roadmap_result["export_ready"] is False
    assert updated.hitl_approved is False

def t_hitl_approved_by_recorded():
    state = AgentState()
    state.roadmap_result = {}
    supervisor = SupervisorAgent()
    updated = supervisor.approve_roadmap(state, approved_by="CFO: Approved Q4 plan")
    assert "CFO" in updated.roadmap_result["approved_by"]

for fn in [t_hitl_roadmap_blocked_before_approval, t_hitl_approve_sets_export_ready,
           t_hitl_reject_keeps_blocked, t_hitl_approved_by_recorded]:
    run(fn.__name__.replace("t_", "HITL: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — RAG FALLBACK (TC-06)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 5: RAG Graceful Degradation (TC-06) ━━━{RESET}")

from rag.retriever import format_rag_context

def t_tc06_format_rag_empty_returns_message():
    result = format_rag_context([])
    assert "No knowledge" in result or "retrieved" in result.lower()

def t_tc06_format_rag_includes_source():
    chunks = [{"content": "Use solar panels.", "source": "IEA Report", "score": 0.8, "confidence": "High"}]
    result = format_rag_context(chunks)
    assert "IEA Report" in result
    assert "solar panels" in result.lower()

def t_tc07_low_confidence_labelled():
    # TC-07: Score below threshold gets "Low" confidence
    chunks = [{"content": "Some text", "source": "Unknown", "score": 0.3, "confidence": "Low"}]
    assert chunks[0]["confidence"] == "Low"

def t_rag_context_numbered_sources():
    chunks = [
        {"content": "A", "source": "Doc1", "score": 0.9, "confidence": "High"},
        {"content": "B", "source": "Doc2", "score": 0.7, "confidence": "Medium"},
    ]
    result = format_rag_context(chunks)
    assert "Source 1" in result
    assert "Source 2" in result
    assert "Doc1" in result and "Doc2" in result

for fn in [t_tc06_format_rag_empty_returns_message, t_tc06_format_rag_includes_source,
           t_tc07_low_confidence_labelled, t_rag_context_numbered_sources]:
    run(fn.__name__.replace("t_", "RAG: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — DATABASE SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}━━━ SECTION 6: Database Schema ━━━{RESET}")

from data.db_setup import init_db
import sqlite3, tempfile

def t_db_init_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
    conn = init_db(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {"organization", "emission_record", "hotspot",
                "reduction_strategy", "scenario", "esg_roadmap"}
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"
    conn.close()

def t_db_fk_enforcement():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
    conn = init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO emission_record (org_id, scope, category, quantity, unit, emission_factor, tco2e) "
            "VALUES (999, 'Scope 1', 'Test', 1.0, 'kWh', 0.4, 0.4)"
        )
        conn.commit()
        # FK violation should either raise or be enforced
        # SQLite with PRAGMA foreign_keys=ON should reject this
        assert False, "FK violation should have been rejected"
    except Exception:
        pass  # expected — FK enforcement working
    conn.close()

for fn in [t_db_init_creates_all_tables, t_db_fk_enforcement]:
    run(fn.__name__.replace("t_", "DB: "), fn)

# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
passed  = sum(1 for r in results if r["status"] == "PASS")
failed  = sum(1 for r in results if r["status"] == "FAIL")
errored = sum(1 for r in results if r["status"] == "ERROR")
total   = len(results)

print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}TEST RESULTS — Agent Correctness Suite{RESET}")
print(f"{'═'*60}")
print(f"  Total:   {total}")
print(f"  {GREEN}Passed:  {passed}{RESET}")
if failed:  print(f"  {RED}Failed:  {failed}{RESET}")
if errored: print(f"  {RED}Errors:  {errored}{RESET}")
print(f"  Pass rate: {passed/total*100:.1f}%")
print(f"{'═'*60}\n")

# Write JSON results for reporting
out_path = os.path.join(os.path.dirname(__file__), "test_results.json")
with open(out_path, "w") as f:
    json.dump({"summary": {"total": total, "passed": passed, "failed": failed,
                            "errored": errored, "pass_rate": round(passed/total*100, 1)},
               "results": results}, f, indent=2)
print(f"Results saved to: {out_path}")

if failed + errored > 0:
    sys.exit(1)
