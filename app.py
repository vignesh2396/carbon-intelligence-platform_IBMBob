"""
app.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Enterprise Carbon Intelligence & Net-Zero Planning Platform
          Streamlit Application — Main Entry Point

          Implements the full user journey defined in Phase 3 (UX Design):
          Step 1: Data Input → Step 2: Analysis → Step 3: Strategies →
          Step 4: Scenarios → Step 5: Roadmap → Step 6: HITL Review & Export

Responsible AI Disclaimer displayed on every page.
HITL gate enforced before roadmap export.

Dependencies: streamlit, plotly, pandas, all agents
"""

from __future__ import annotations

import os
import io
import sys

# ── Path setup ────────────────────────────────────────────────────────────────
# Ensure the project root is on sys.path for all imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Environment loading ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.validators import validate_emissions_csv
from agents.supervisor_agent import SupervisorAgent, AgentState
from data.db_setup import init_db
from utils.guardrails import (
    run_all_input_guardrails,
    run_all_output_guardrails,
    record_token_usage,
    get_operational_stats,
)
from utils.performance_dashboard import render_performance_dashboard

# ─────────────────────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carbon Intelligence Platform",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a472a, #2d6a4f);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: #f0f9f0;
        border-left: 4px solid #2d6a4f;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .hitl-banner {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .approved-banner {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .disclaimer {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 0.75rem;
        font-size: 0.85rem;
        color: #6c757d;
        margin-top: 1rem;
    }
    .agent-badge {
        background: #e8f5e9;
        border: 1px solid #4caf50;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.8rem;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────────────────────
def init_session_state() -> None:
    """Initialize all session state keys for agent memory across interactions."""
    defaults = {
        "agent_state":     None,   # AgentState object
        "pipeline_run":    False,  # Whether the pipeline has been executed
        "active_tab":      0,
        "org_name":        "My Organization",
        "budget_usd":      500_000.0,
        "target_year":     2030,
        "hitl_approved":   False,
        "hitl_rejected":   False,
        "progress_log":    [],
        "db_initialized":  False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()

# Initialize database on first run
if not st.session_state["db_initialized"]:
    try:
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌿 Enterprise Carbon Intelligence & Net-Zero Planning Platform</h1>
    <p>Agentic AI-powered sustainability analytics | Scope 1 · Scope 2 · Scope 3 | GHG Protocol Aligned</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Configuration
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    st.session_state["org_name"] = st.text_input(
        "Organization Name",
        value=st.session_state["org_name"]
    )
    st.session_state["budget_usd"] = st.number_input(
        "Decarbonization Budget (USD)",
        min_value=10_000.0,
        max_value=10_000_000.0,
        value=st.session_state["budget_usd"],
        step=50_000.0,
        format="%.0f",
    )
    st.session_state["target_year"] = st.selectbox(
        "Net-Zero Target Year",
        options=[2030, 2035, 2040, 2045, 2050],
        index=[2030, 2035, 2040, 2045, 2050].index(st.session_state["target_year"]),
    )

    st.divider()
    st.markdown("**🤖 Active Agents**")
    agents = [
        "1. Carbon Accounting Agent",
        "2. Emissions Analysis Agent",
        "3. Reduction Strategy Agent",
        "4. Scenario Simulation Agent",
        "5. Cost & Feasibility Agent",
        "6. ESG Roadmap Agent",
        "Ω. Supervisor Agent",
    ]
    for a in agents:
        st.markdown(f'<span class="agent-badge">{a}</span>', unsafe_allow_html=True)
        st.write("")

    st.divider()
    st.markdown("""
    <div class="disclaimer">
    ⚠️ <strong>Responsible AI Disclaimer</strong><br>
    AI-generated results are estimates based on GHG Protocol emission factors.
    Recommendations require professional validation before regulatory use.
    No personal data is collected or stored.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main Content — Tabbed Interface
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📁 1. Data Input",
    "📊 2. Emissions Analysis",
    "💡 3. Strategies",
    "📈 4. Scenarios",
    "🗺️ 5. ESG Roadmap",
    "✅ 6. Review & Export",
    "📊 Performance Dashboard",
])


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Data Input
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.header("📁 Step 1: Upload Emissions Activity Data")
    st.write("Upload your organization's activity data as a CSV file, or use the sample data.")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help="Required columns: activity, category, scope, quantity, unit, business_unit"
        )

    with col2:
        use_sample = st.button("📥 Use Sample Data", use_container_width=True)
        st.caption("Load pre-configured sample organization data")

    # Load data source
    df_to_use = None
    if uploaded_file:
        df_to_use = pd.read_csv(uploaded_file)
        st.success(f"✅ Uploaded: {uploaded_file.name} ({len(df_to_use)} rows)")
    elif use_sample:
        sample_path = os.path.join(PROJECT_ROOT, "data", "sample_org_data.csv")
        if os.path.exists(sample_path):
            df_to_use = pd.read_csv(sample_path)
            st.success(f"✅ Sample data loaded ({len(df_to_use)} rows)")
        else:
            st.error("Sample data file not found.")

    if df_to_use is not None:
        st.subheader("Data Preview")
        st.dataframe(df_to_use, use_container_width=True)

        # Validation
        validation = validate_emissions_csv(df_to_use)

        if validation.errors:
            st.error("**Validation Errors — Please fix before proceeding:**")
            for err in validation.errors:
                st.error(f"• {err}")
        else:
            if validation.warnings:
                for warn in validation.warnings:
                    st.warning(f"⚠️ {warn}")

            st.success("✅ Data validation passed!")

            # Run pipeline button
            st.divider()
            run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
            with run_col2:
                if st.button(
                    "🚀 Run AI Analysis Pipeline",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Initializing AI agents..."):
                        # Progress tracking
                        progress_bar = st.progress(0)
                        status_text  = st.empty()

                        def progress_callback(step_name: str, step_num: int, total: int):
                            progress_bar.progress(step_num / total)
                            status_text.text(f"⚙️ Running: {step_name} ({step_num}/{total})")

                        try:
                            # ── Input Guardrails on org_name ──────────────
                            org_guard = run_all_input_guardrails(
                                st.session_state.get("org_name", ""),
                                session_id=str(id(st.session_state)),
                            )
                            if org_guard.blocked:
                                st.error(f"⚠️ Input blocked by guardrail: {', '.join(org_guard.violations)}")
                                st.stop()

                            import time as _time
                            _start = _time.time()
                            supervisor = SupervisorAgent()
                            state = supervisor.run_full_pipeline(
                                activity_df=validation.clean_df,
                                org_name=st.session_state["org_name"],
                                budget_usd=st.session_state["budget_usd"],
                                target_year=st.session_state["target_year"],
                                progress_callback=progress_callback,
                            )
                            _latency = (_time.time() - _start) * 1000
                            record_token_usage(
                                len(str(validation.clean_df)) // 4,
                                len(str(state.roadmap_result)) // 4,
                                cost_usd=0.005,
                            )
                            st.session_state["session_metrics"] = {"avg_latency_ms": _latency}
                            st.session_state["agent_state"]  = state
                            st.session_state["pipeline_run"] = True
                            progress_bar.progress(1.0)
                            status_text.text("✅ Pipeline complete!")
                            st.success(
                                "🎉 Analysis complete! Navigate to the tabs above to explore results."
                            )
                        except Exception as e:
                            st.error(f"Pipeline error: {e}")

    # Required CSV format reference
    with st.expander("📋 Required CSV Format"):
        st.markdown("""
        | Column | Description | Example |
        |--------|-------------|---------|
        | `activity` | Description of the activity | "Electricity consumption - Head Office" |
        | `category` | Emission category | "Purchased Electricity" |
        | `scope` | GHG Protocol scope | "Scope 1", "Scope 2", or "Scope 3" |
        | `quantity` | Numeric quantity (must be positive) | 850000 |
        | `unit` | Unit of measurement | "kWh", "litre", "pkm", "tonne", "USD" |
        | `business_unit` | Organizational unit | "Operations", "Manufacturing" |
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Check pipeline has run
# ─────────────────────────────────────────────────────────────────────────────
def check_pipeline() -> AgentState | None:
    if not st.session_state["pipeline_run"] or st.session_state["agent_state"] is None:
        st.info("👆 Run the AI Analysis Pipeline in **Step 1: Data Input** first.")
        return None
    return st.session_state["agent_state"]


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Emissions Analysis
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.header("📊 Step 2: Emissions Analysis")
    state = check_pipeline()

    if state:
        acc = state.accounting_result
        ana = state.analysis_result

        # ── KPI Row ────────────────────────────────────────────────────────
        st.subheader("📊 Emission Summary")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Emissions", f"{acc.get('total_tco2e', 0):,.1f} tCO₂e")
        k2.metric("Scope 1 (Direct)",     f"{acc.get('scope1_tco2e', 0):,.1f} tCO₂e")
        k3.metric("Scope 2 (Electricity)", f"{acc.get('scope2_tco2e', 0):,.1f} tCO₂e")
        k4.metric("Scope 3 (Value Chain)", f"{acc.get('scope3_tco2e', 0):,.1f} tCO₂e")

        if ana.get("high_emission_flag"):
            st.markdown("""
            <div class="hitl-banner">
            ⚠️ <strong>HIGH-EMISSION ORGANIZATION DETECTED</strong><br>
            Total emissions exceed 5,000 tCO₂e. Human review is required before the ESG roadmap
            is finalized. This requirement is enforced at Step 6.
            </div>
            """, unsafe_allow_html=True)

        # ── Charts ────────────────────────────────────────────────────────
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            scope_data = ana.get("scope_breakdown", [])
            if scope_data:
                fig = px.pie(
                    pd.DataFrame(scope_data),
                    values="tco2e",
                    names="scope",
                    title="Emissions by Scope",
                    color_discrete_sequence=["#1a472a", "#2d6a4f", "#52b788"],
                )
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            bu_data = ana.get("bu_breakdown", [])
            if bu_data:
                df_bu = pd.DataFrame(bu_data)
                fig = px.bar(
                    df_bu,
                    x="tco2e",
                    y="business_unit",
                    orientation="h",
                    title="Emissions by Business Unit (tCO₂e)",
                    color="tco2e",
                    color_continuous_scale=["#d4edda", "#1a472a"],
                    labels={"tco2e": "tCO₂e", "business_unit": "Business Unit"},
                )
                st.plotly_chart(fig, use_container_width=True)

        # ── Hotspot Table ─────────────────────────────────────────────────
        st.subheader("🔥 Top Carbon Hotspots")
        hotspots = ana.get("hotspots", [])
        if hotspots:
            df_hot = pd.DataFrame(hotspots)
            df_hot["tco2e"] = df_hot["tco2e"].map("{:,.2f}".format)
            df_hot["pct_contribution"] = df_hot["pct_contribution"].map("{:.1f}%".format)
            st.dataframe(
                df_hot[["rank", "activity", "scope", "business_unit", "tco2e", "pct_contribution"]],
                use_container_width=True,
                hide_index=True,
            )

        # ── Explainability ────────────────────────────────────────────────
        with st.expander("🔍 AI Analysis Reasoning"):
            st.write(ana.get("analysis_narrative", ""))
            st.caption(f"Performed by: {acc.get('agent', 'Carbon Accounting Agent')}, "
                      f"{ana.get('agent', 'Emissions Analysis Agent')}")
            st.markdown(f"""
            <div class="disclaimer">{acc.get('disclaimer', '')}</div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Reduction Strategies
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.header("💡 Step 3: Reduction Strategy Recommendations")
    state = check_pipeline()

    if state:
        strat = state.strategy_result
        feas  = state.feasibility_result

        st.markdown(feas.get("narrative", ""))

        # ── Priority Breakdown ────────────────────────────────────────────
        p1, p2, p3 = st.columns(3)
        p1.metric("🟢 High Priority",   len(feas.get("high_priority", [])))
        p2.metric("🟡 Medium Priority", len(feas.get("medium_priority", [])))
        p3.metric("🔴 Low Priority",    len(feas.get("low_priority", [])))

        # ── Ranked Strategy Table ─────────────────────────────────────────
        scored = feas.get("scored_strategies", [])
        if scored:
            st.subheader("📋 Ranked Strategies (by Composite Score)")
            rows = []
            for s in scored:
                rows.append({
                    "Priority":    s.get("priority", ""),
                    "Strategy":    s.get("strategy_name", ""),
                    "Hotspot":     s.get("hotspot_activity", "")[:50],
                    "Reduction (tCO₂e)": f"{float(s.get('estimated_reduction_tco2e', 0)):,.1f}",
                    "Cost (USD)":  f"${float(s.get('estimated_cost_usd', 0)):,.0f}",
                    "Feasibility": f"{float(s.get('feasibility_score', 0)):.0%}",
                    "Score":       f"{float(s.get('composite_score', 0)):.3f}",
                    "Timeframe":   s.get("timeframe", ""),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Strategies by Hotspot ─────────────────────────────────────────
        st.subheader("🔥 Strategies per Hotspot")
        strategies_by_hotspot = strat.get("strategies_by_hotspot", {})
        for hotspot_activity, strategies in strategies_by_hotspot.items():
            with st.expander(f"📌 {hotspot_activity}"):
                for i, s in enumerate(strategies, 1):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{i}. {s.get('strategy_name', 'Strategy')}**")
                        st.write(s.get("description", ""))
                        if s.get("confidence_note"):
                            st.warning(s["confidence_note"])
                    with col_b:
                        st.metric("Est. Reduction", f"{float(s.get('estimated_reduction_tco2e', 0)):,.0f} tCO₂e")
                        st.metric("Est. Cost", f"${float(s.get('estimated_cost_usd', 0)):,.0f}")
                        st.metric("Feasibility", f"{float(s.get('feasibility_score', 0)):.0%}")
                    # Explainability — show RAG sources
                    sources = s.get("rag_sources", [])
                    if sources:
                        st.caption(f"📚 Sources: {' | '.join(sources)}")
                    st.divider()

        # RAG sources summary
        all_sources = strat.get("rag_sources_used", [])
        if all_sources:
            st.info(f"**Knowledge Base Sources Used:** {', '.join(all_sources)}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — Scenarios
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.header("📈 Step 4: Decarbonization Scenario Simulation")
    state = check_pipeline()

    if state:
        scen = state.scenario_result

        st.markdown(scen.get("narrative", ""))

        bau_result     = scen.get("bau", {})
        int_result     = scen.get("intervention", {})
        year_labels    = bau_result.get("year_labels", [])
        bau_curve      = bau_result.get("bau_curve", [])
        int_curve      = int_result.get("intervention_curve", [])

        # ── KPIs ──────────────────────────────────────────────────────────
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "BAU Cumulative (3yr)",
            f"{bau_result.get('total_bau_tco2e', 0):,.0f} tCO₂e"
        )
        m2.metric(
            "With Interventions (3yr)",
            f"{int_result.get('total_intervention_tco2e', 0):,.0f} tCO₂e",
            delta=f"-{int_result.get('total_reduction_pct', 0):.1f}%",
        )
        m3.metric(
            "Net-Zero Trajectory",
            int_result.get("net_zero_year") or "Beyond horizon"
        )

        # ── Comparison Chart ──────────────────────────────────────────────
        if year_labels and bau_curve:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=year_labels, y=bau_curve,
                mode="lines+markers",
                name="Business As Usual",
                line=dict(color="#dc3545", width=3, dash="dash"),
                marker=dict(size=8),
            ))
            fig.add_trace(go.Scatter(
                x=year_labels, y=int_curve,
                mode="lines+markers",
                name="With AI-Recommended Interventions",
                line=dict(color="#28a745", width=3),
                marker=dict(size=8),
            ))
            fig.update_layout(
                title="Emission Trajectory: BAU vs. Intervention",
                xaxis_title="Year",
                yaxis_title="tCO₂e",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                plot_bgcolor="#f8f9fa",
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Explainability ────────────────────────────────────────────────
        with st.expander("🔍 Simulation Methodology"):
            st.markdown("""
            **BAU Scenario**: Projects emissions growing at 2% annually with no interventions.

            **Intervention Scenario**: Applies High and Medium priority strategies from Step 3.
            Reductions are phased based on each strategy's implementation timeframe.
            Reductions are cumulative — once implemented, they persist.

            *Model source: GHG Protocol accounting + linear reduction model.
            Projections are estimates for planning purposes only.*
            """)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5 — ESG Roadmap
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.header("🗺️ Step 5: ESG Decarbonization Roadmap")
    state = check_pipeline()

    if state:
        roadmap = state.roadmap_result

        status = roadmap.get("status", "AWAITING_APPROVAL")
        if status == "APPROVED":
            st.markdown("""
            <div class="approved-banner">
            ✅ <strong>ROADMAP APPROVED</strong> — This roadmap has been reviewed and approved.
            You may export it from Step 6.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="hitl-banner" style="color:#856404;">
            🔒 <strong>AWAITING HUMAN APPROVAL</strong> — This AI-generated roadmap must be
            reviewed and approved in <strong>Step 6: Review &amp; Export</strong> before it can be exported.
            This is an AI safety control.
            </div>
            """, unsafe_allow_html=True)

        # ── KPIs ──────────────────────────────────────────────────────────
        kpis = roadmap.get("kpis", {})
        if kpis:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Baseline Emissions", kpis.get("baseline_tco2e", "—"))
            k2.metric("Projected 3yr Reduction", kpis.get("projected_3yr_reduction_pct", "—"))
            k3.metric("Investment Required", kpis.get("total_investment_required", "—"))
            k4.metric("Strategies Implemented", kpis.get("strategies_implemented", "—"))

        # ── Milestones ────────────────────────────────────────────────────
        milestones = roadmap.get("milestones", [])
        if milestones:
            st.subheader("📅 Implementation Milestones")
            for m in milestones:
                with st.expander(
                    f"🎯 {m['phase']} — Reduce by {m['tco2e_reduction']:,.1f} tCO₂e | "
                    f"Investment: ${m['investment']:,.0f}"
                ):
                    for action in m["actions"]:
                        st.markdown(f"• {action}")

        # ── Full Roadmap Narrative ────────────────────────────────────────
        st.subheader("📄 Full Roadmap Narrative")
        st.text_area(
            "AI-Generated Roadmap",
            value=roadmap.get("roadmap_text", ""),
            height=400,
            disabled=True,
        )

        st.markdown("""
        <div class="disclaimer">
        This roadmap was generated by an Agentic AI system. It requires validation by a
        certified sustainability professional before use in regulatory reporting or
        formal ESG disclosures. All emission estimates are based on GHG Protocol factors.
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 6 — Human-in-the-Loop Review & Export
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.header("✅ Step 6: Human Review & Approval (HITL Gate)")
    state = check_pipeline()

    if state:
        roadmap = state.roadmap_result
        status  = roadmap.get("status", "AWAITING_APPROVAL")

        # ── HITL Status Banner ─────────────────────────────────────────────
        if status == "APPROVED":
            st.markdown("""
            <div class="approved-banner">
            ✅ <strong>ROADMAP APPROVED AND READY FOR EXPORT</strong>
            </div>
            """, unsafe_allow_html=True)

        elif status == "REJECTED":
            st.error(
                f"❌ Roadmap was REJECTED. "
                f"Reason: {roadmap.get('rejection_reason', 'Not specified')}"
            )

        else:
            st.markdown("""
            <div class="hitl-banner" style="color:#856404;">
            <h4>🔒 Human Review Required</h4>
            <p>This AI-generated ESG roadmap requires your review and explicit approval before export.
            Please review the roadmap in <strong>Step 5</strong>, then approve or reject below.</p>
            <p><strong>Why is this approval needed?</strong><br>
            High-impact sustainability commitments affect organizational strategy, finance, and
            regulatory reporting. AI-generated recommendations must be validated by qualified
            professionals. This is an AI safety control consistent with Responsible AI principles.</p>
            </div>
            """, unsafe_allow_html=True)

        # ── Review Summary ─────────────────────────────────────────────────
        st.subheader("📋 Review Summary")
        acc = state.accounting_result
        ana = state.analysis_result
        feas = state.feasibility_result

        rev_col1, rev_col2 = st.columns(2)
        with rev_col1:
            st.markdown("**Emissions Summary**")
            st.write(f"• Total: **{acc.get('total_tco2e', 0):,.2f} tCO₂e**")
            st.write(f"• Scope 1: {acc.get('scope1_tco2e', 0):,.2f} tCO₂e")
            st.write(f"• Scope 2: {acc.get('scope2_tco2e', 0):,.2f} tCO₂e")
            st.write(f"• Scope 3: {acc.get('scope3_tco2e', 0):,.2f} tCO₂e")
        with rev_col2:
            st.markdown("**Strategy Summary**")
            st.write(f"• High priority strategies: {len(feas.get('high_priority', []))}")
            st.write(f"• Medium priority strategies: {len(feas.get('medium_priority', []))}")
            st.write(f"• Investment required: ${feas.get('total_investment_required', 0):,.0f}")
            st.write(f"• High emission flag: {'⚠️ Yes' if ana.get('high_emission_flag') else '✅ No'}")

        # ── HITL Approval / Rejection Buttons ─────────────────────────────
        if status not in ("APPROVED", "REJECTED"):
            st.divider()
            st.subheader("🧑‍💼 Reviewer Decision")

            reviewer_name = st.text_input(
                "Reviewer Name / Role",
                placeholder="e.g. Head of Sustainability, CFO",
            )
            review_notes = st.text_area(
                "Review Notes (optional)",
                placeholder="Add any comments or conditions for approval...",
                height=100,
            )

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button(
                    "✅ APPROVE Roadmap",
                    type="primary",
                    use_container_width=True,
                    disabled=not reviewer_name,
                ):
                    supervisor = SupervisorAgent()
                    updated_state = supervisor.approve_roadmap(
                        state,
                        approved_by=f"{reviewer_name}: {review_notes or 'Approved without notes'}"
                    )
                    st.session_state["agent_state"] = updated_state
                    st.session_state["hitl_approved"] = True
                    st.success("✅ Roadmap approved! You may now export below.")
                    st.rerun()

            with btn_col2:
                if st.button(
                    "❌ REJECT Roadmap",
                    type="secondary",
                    use_container_width=True,
                    disabled=not reviewer_name,
                ):
                    supervisor = SupervisorAgent()
                    updated_state = supervisor.reject_roadmap(
                        state,
                        reason=review_notes or "Rejected without reason given."
                    )
                    st.session_state["agent_state"] = updated_state
                    st.session_state["hitl_rejected"] = True
                    st.warning("❌ Roadmap rejected. Return to Step 1 to adjust inputs.")
                    st.rerun()

            if not reviewer_name:
                st.caption("⚠️ Reviewer Name is required before approving or rejecting.")

        # ── Export (only available after APPROVED) ─────────────────────────
        if status == "APPROVED":
            st.divider()
            st.subheader("📤 Export Approved Roadmap")

            roadmap_text = roadmap.get("roadmap_text", "")
            kpis         = roadmap.get("kpis", {})
            export_text = f"""ENTERPRISE CARBON INTELLIGENCE PLATFORM
ESG Net-Zero Decarbonization Roadmap
Organization: {state.org_name}
Status: APPROVED
Approved by: {roadmap.get('approved_by', 'N/A')}
Generated: AI-assisted (GHG Protocol aligned)

KEY PERFORMANCE INDICATORS
{'='*50}
Baseline Emissions:        {kpis.get('baseline_tco2e', '—')}
Projected 3yr Reduction:   {kpis.get('projected_3yr_reduction_pct', '—')}
Total Investment Required: {kpis.get('total_investment_required', '—')}
Net-Zero Target Year:      {kpis.get('target_year', '—')}
Strategies Implemented:    {kpis.get('strategies_implemented', '—')}

ROADMAP
{'='*50}
{roadmap_text}

DISCLAIMER
{'='*50}
This roadmap was generated by an Agentic AI system and approved by a human reviewer.
Emission estimates are based on GHG Protocol factors (2023).
This document should be validated by a certified sustainability professional before
use in regulatory filings, ESG disclosures, or investor communications.
"""
            st.download_button(
                label="⬇️ Download Approved Roadmap (.txt)",
                data=export_text,
                file_name=f"{state.org_name.replace(' ', '_')}_ESG_Roadmap_APPROVED.txt",
                mime="text/plain",
                use_container_width=True,
                type="primary",
            )

        # ── Agent Audit Trail ──────────────────────────────────────────────
        with st.expander("🔍 Agent Audit Trail"):
            st.markdown("**Completed Pipeline Steps:**")
            for step in state.completed_steps:
                st.markdown(f"✅ {step}")
            if state.errors:
                st.markdown("**⚠️ Pipeline Warnings:**")
                for err in state.errors:
                    st.warning(err)
            st.caption(
                f"Organization: {state.org_name} | "
                f"Budget: ${state.budget_usd:,.0f} | "
                f"Target Year: {state.target_year}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
with tab7:
    render_performance_dashboard(st.session_state.get("session_metrics", {}))

st.divider()
st.markdown("""
<div style="text-align: center; color: #6c757d; font-size: 0.85rem; padding: 1rem 0;">
    Enterprise Carbon Intelligence & Net-Zero Planning Platform<br>
    Built with Agentic AI (LangChain · Gemini) · GHG Protocol Aligned ·
    Responsible AI Principles Applied<br>
    IBM SkillsBuild Capstone Project 2026
</div>
""", unsafe_allow_html=True)
