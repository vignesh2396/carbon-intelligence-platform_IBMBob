# Test Cases — Enterprise Carbon Intelligence Platform
# Guideline Requirement: §8.6 — Minimum 5 test scenarios
# ─────────────────────────────────────────────────────

## TC-01 — Normal Use Case: Full Emissions Analysis

**Scenario**: Sustainability Manager uploads complete organizational activity data.

**Input**:
```
activity,category,scope,quantity,unit,business_unit
Electricity consumption,Purchased Electricity,Scope 2,850000,kWh,Operations
Natural gas,Stationary Combustion,Scope 1,120000,kWh,Operations
Air travel,Business Travel,Scope 3,420000,pkm,All Departments
```

**Expected Output**:
- ✅ Scope 1, 2, 3 breakdown calculated correctly
- ✅ Top-5 hotspots ranked by tCO₂e
- ✅ ≥3 strategies per hotspot with RAG sources
- ✅ BAU vs. intervention scenario chart rendered
- ✅ ESG roadmap generated with status = AWAITING_APPROVAL
- ✅ HITL gate active — export blocked until approved

**Pass Criteria**: All 6 pipeline steps complete; results displayed in all 5 tabs.

---

## TC-02 — Alternative Scenario: Single Scope Only

**Scenario**: Organization only tracks electricity consumption (Scope 2).

**Input**:
```
activity,category,scope,quantity,unit,business_unit
Electricity - HQ,Purchased Electricity,Scope 2,2500000,kWh,Operations
```

**Expected Output**:
- ✅ Scope 2 total: 2500000 × 0.433 / 1000 = 1082.5 tCO₂e
- ✅ Scope 1 = 0, Scope 3 = 0
- ✅ Hotspot = "Electricity - HQ"
- ✅ Strategies include: renewable PPAs, on-site solar, energy efficiency
- ✅ High emission flag = YES (>5000 tCO₂e: NO — 1082.5 < threshold; HITL still active via roadmap)

**Pass Criteria**: Single-scope analysis works end-to-end; correct tCO₂e math.

---

## TC-03 — Missing Information: Required Column Absent

**Scenario**: User uploads CSV missing the 'quantity' column.

**Input**:
```
activity,category,scope,unit,business_unit
Electricity,Purchased Electricity,Scope 2,kWh,Operations
```

**Expected Output**:
- ✅ Validation error displayed: "Missing required column(s): quantity"
- ✅ "Run AI Analysis Pipeline" button is NOT shown
- ✅ No agents are invoked
- ✅ User is guided to fix the CSV

**Pass Criteria**: System fails gracefully with clear error; no agent execution.

---

## TC-04 — Invalid Input: Negative Quantity Values

**Scenario**: User uploads CSV with negative quantity in one row.

**Input**:
```
activity,category,scope,quantity,unit,business_unit
Electricity,Purchased Electricity,Scope 2,-500,kWh,Operations
Fuel,Stationary Combustion,Scope 1,1000,litre,Operations
```

**Expected Output**:
- ✅ Validation error: "'quantity' must be a positive number. Negative or zero values found in row(s): [2]"
- ✅ Pipeline not invoked
- ✅ Row 2 is identified (1-based, including header)

**Pass Criteria**: Negative values caught at validation; helpful row number shown.

---

## TC-05 — Escalation / HITL: High-Emission Organization

**Scenario**: Large manufacturing organization with total emissions > 5,000 tCO₂e.

**Input**: sample_org_data.csv (total > 5,000 tCO₂e from electricity + fuel + travel combined)

**Expected Output**:
- ✅ `high_emission_flag = True`
- ✅ Yellow warning banner: "HIGH-EMISSION ORGANIZATION DETECTED" in Tab 2
- ✅ ESG Roadmap status = AWAITING_APPROVAL
- ✅ Export button disabled until human approves in Tab 6
- ✅ Reviewer Name field required before approval button activates
- ✅ On approval: status changes to APPROVED; export button becomes active
- ✅ Approved_by field populated in exported document

**Pass Criteria**: HITL gate enforced; roadmap not exportable without human action.

---

## TC-06 — RAG Failure: No Documents in Knowledge Base, No API Key

**Scenario**: Chroma DB is empty (no PDFs added) AND GOOGLE_API_KEY is not set.

**Simulated Condition**: 
- `rag/documents/` folder is empty
- GOOGLE_API_KEY env var removed

**Expected Output**:
- ✅ RAG pipeline falls back to built-in knowledge base (5 fallback documents)
- ✅ Strategies are generated from fallback knowledge base
- ✅ Confidence indicator shown as "Medium" or "Low" where RAG confidence is limited
- ✅ Warning note displayed: "Low RAG confidence for this hotspot..."
- ✅ Application does NOT crash; user-friendly error if LLM fails
- ✅ Fallback strategy returned with disclaimer

**Pass Criteria**: Graceful degradation; system remains usable with reduced quality.

---

## TC-07 — Low Confidence: Ambiguous Activity Description

**Scenario**: Activity category is unrecognized by the emission factor map.

**Input**:
```
activity,category,scope,quantity,unit,business_unit
Miscellaneous operations,Other,Scope 3,5000,USD,Unknown
```

**Expected Output**:
- ✅ System uses fallback emission factor (procurement_usd default)
- ✅ Warning shown: "Unrecognised unit(s)" or appropriate notice
- ✅ Strategy confidence note shown: "Low confidence" with recommendation to verify
- ✅ Results include disclaimer about uncertain emission category

**Pass Criteria**: System handles unknown categories gracefully; confidence communicated.
