# 🌿 Enterprise Carbon Intelligence & Net-Zero Planning Platform

> **IBM SkillsBuild Capstone 2026 — Agentic AI Project**
> Domain: Sustainability / ESG | Agentic AI · RAG · Multi-Agent · Human-in-the-Loop

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/Framework-LangChain-green)](https://langchain.com)
[![Tests](https://img.shields.io/badge/Tests-34%2F34%20Passing-brightgreen)](#testing)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Project Overview

| Field | Detail |
|-------|--------|
| **Domain** | Sustainability / ESG |
| **Problem** | Organizations measure carbon but lack intelligence to evaluate which interventions yield the best environmental and financial outcomes |
| **Solution** | Agentic AI platform: activity data → hotspots → strategies → simulation → HITL-approved roadmap |
| **Target Users** | Sustainability Managers, CFOs, ESG Auditors, Operations Directors |
| **LLM** | Google Gemini 1.5 Pro (guideline-preferred) |
| **UI** | Streamlit (guideline-preferred) |
| **Knowledge Sources** | GHG Protocol, IPCC AR6, Science Based Targets (SBTi) |

---

## 🤖 AI Agent Architecture

```
User (Streamlit UI)
    └─▶ Supervisor Agent ──── orchestrates ────────────────────────────────┐
            │                                                                │
            ├──▶ [1] Carbon Accounting Agent   ← Tool: emissions_calculator │
            │         GHG Protocol Scope 1/2/3 calculation                  │
            │                                                                │
            ├──▶ [2] Emissions Analysis Agent  ← Tool: hotspot_identifier   │
            │         Rank top hotspots by tCO₂e contribution               │
            │                                                                │
            ├──▶ [3] Reduction Strategy Agent  ← RAG ──▶ InMemoryVectorStore│
            │         LLM: Gemini 1.5 Pro + GHG Protocol / IPCC / SBTi     │
            │                                                                │
            ├──▶ [4] Cost & Feasibility Agent  ← Tool: feasibility_scorer   │
            │         Composite scoring: 0.5×reduction + 0.3×feas - 0.2×cost│
            │                                                                │
            ├──▶ [5] Scenario Simulation Agent ← Tool: scenario_simulator   │
            │         BAU vs. intervention curves over 3-year horizon        │
            │                                                                │
            └──▶ [6] ESG Roadmap Agent         ← LLM: Gemini 1.5 Pro       │
                      Status: AWAITING_APPROVAL (HITL gate enforced)         │
                                                                             │
                ─────────────── HUMAN-IN-THE-LOOP GATE ────────────────────  │
                Human reviewer APPROVE/REJECT in Streamlit Tab 6             │
                ▶ [EXPORT] Approved ESG Roadmap (.txt)  ◀───────────────────┘
```

### Agent Responsibilities

| Agent | Responsibility |
|-------|---------------|
| **Supervisor Agent** | Orchestrates pipeline, maintains AgentState memory, enforces HITL |
| **Carbon Accounting Agent** | Applies GHG Protocol factors, calculates Scope 1/2/3 tCO₂e |
| **Emissions Analysis Agent** | Ranks hotspots, % contributions, flags high-emission orgs |
| **Reduction Strategy Agent** | RAG retrieval + LLM synthesis of 3 strategies per hotspot |
| **Cost & Feasibility Agent** | Composite scoring, priority labelling, budget fit |
| **Scenario Simulation Agent** | BAU vs. intervention curve modeling over 3-year horizon |
| **ESG Roadmap Agent** | LLM-generated phased roadmap, milestone planning, HITL gate |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini 1.5 Pro |
| **Agent Framework** | LangChain (supervisor pattern) |
| **RAG / Vector Store** | `langchain_core.vectorstores.InMemoryVectorStore` |
| **Embeddings** | Google `text-embedding-004` |
| **UI** | Streamlit |
| **Database** | SQLite |
| **Data Processing** | pandas, numpy |
| **Visualization** | Plotly |
| **Language** | Python 3.11+ |

---

## 📁 Project Structure

```
carbon-intelligence-platform/
├── app.py                           ← Streamlit entry point (6 tabs + HITL)
├── requirements.txt
├── .env.example                     ← Copy to .env — add API keys here
│
├── agents/
│   ├── supervisor_agent.py          ← Pipeline orchestration + HITL gate
│   ├── carbon_accounting_agent.py   ← Scope 1/2/3 calculation
│   ├── emissions_analysis_agent.py  ← Hotspot identification
│   ├── reduction_strategy_agent.py  ← RAG + LLM strategy generation
│   ├── scenario_simulation_agent.py ← BAU vs. intervention simulation
│   ├── cost_feasibility_agent.py    ← Strategy scoring & ranking
│   └── esg_roadmap_agent.py         ← Roadmap generation (HITL-gated)
│
├── tools/
│   ├── emissions_calculator.py      ← GHG Protocol computation (Tool 1)
│   ├── hotspot_identifier.py        ← Ranking & hotspot analysis (Tool 2)
│   ├── scenario_simulator.py        ← Numerical simulation engine (Tool 3)
│   └── feasibility_scorer.py        ← Composite scoring (Tool 4)
│
├── rag/
│   ├── documents/                   ← Place PDF knowledge sources here
│   ├── embeddings.py                ← Document ingestion & embedding
│   └── retriever.py                 ← InMemoryVectorStore query (Tool 5)
│
├── data/
│   ├── db_setup.py                  ← SQLite schema (6 tables, 4 indexes)
│   └── sample_org_data.csv          ← 14-row sample activity dataset
│
├── utils/
│   ├── logger.py                    ← Structured JSON audit logger
│   ├── validators.py                ← CSV input validation
│   └── helpers.py                   ← GHG factors, unit conversions
│
├── tests/
│   ├── run_tests.py                 ← 34-test correctness suite
│   ├── test_cases.md                ← 7 documented scenarios
│   └── test_results.json            ← Generated test output
│
├── assets/
│   ├── CarbonIntelligencePlatform_Presentation.pptx  ← 12-slide deck
│   └── CarbonIntelligencePlatform_Demo.mp4           ← 40s demo video
│
├── build_ppt.py                     ← Generates PowerPoint
├── build_video.py                   ← Generates MP4 demo video
└── logs/agent_activity.log          ← Generated at runtime
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/vignesh2396/carbon-intelligence-platform_IBMBob.git
cd carbon-intelligence-platform_IBMBob
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:
```
GOOGLE_API_KEY=your_actual_key_here
```

Get a free key at: https://makersuite.google.com/app/apikey

### 5. (Optional) Add PDF Knowledge Sources

Place PDF files in `rag/documents/`:
- GHG Protocol Corporate Standard
- IPCC AR6 Working Group III
- SBTi Net-Zero Standard

The platform includes a built-in fallback knowledge base if no PDFs are added.

### 6. Run the Application

```bash
streamlit run app.py
```

Open: `http://localhost:8501`

---

## 📊 Usage Guide

| Step | Tab | Action |
|------|-----|--------|
| 1 | 📁 Data Input | Upload CSV or click "Use Sample Data", then run pipeline |
| 2 | 📊 Emissions Analysis | View Scope breakdown, hotspot chart, BU comparison |
| 3 | 💡 Strategies | Review RAG-grounded strategies with sources + confidence |
| 4 | 📈 Scenarios | Compare BAU vs. intervention emission trajectories |
| 5 | 🗺️ ESG Roadmap | Review AI-generated 3-year decarbonization roadmap |
| 6 | ✅ Review & Export | **Enter name → APPROVE → Download approved roadmap** |

> ⚠️ **The roadmap cannot be exported until a human reviewer approves it in Step 6.**

---

## 🧪 Testing

Run the full correctness test suite:

```bash
python tests/run_tests.py
```

**Results: 34/34 tests passing (100%)**

| Section | Tests | Coverage |
|---------|-------|----------|
| Tools Layer | 12 | Emissions math, hotspot ranking, simulation, scoring |
| Input Validators | 5 | TC-03 missing column, TC-04 negative values, scope, empty rows |
| Agent Pipeline | 7 | TC-01 full pipeline, TC-02 single scope, TC-05 high-emission |
| HITL Gate | 4 | Approve, reject, blocked state, audit trail |
| RAG Degradation | 4 | TC-06 fallback, TC-07 low confidence, sources |
| Database Schema | 2 | Table creation, FK enforcement |

---

## 📽️ Presentation & Demo

```bash
# Generate 12-slide PowerPoint
python build_ppt.py
# Output: assets/CarbonIntelligencePlatform_Presentation.pptx

# Generate 40-second demo video
python build_video.py
# Output: assets/CarbonIntelligencePlatform_Demo.mp4
```

---

## 🔐 Security & Responsible AI

| Control | Implementation |
|---------|---------------|
| ✅ No API keys in code | All secrets via `.env`; never committed |
| ✅ No PII collected | Session-scoped context only |
| ✅ Input validation | CSV schema enforced before agent invocation |
| ✅ Prompt sanitization | User text cleaned before LLM prompts |
| ✅ Hallucination control | RAG grounding + confidence threshold (0.6) |
| ✅ Audit logging | Every agent decision logged as structured JSON |
| ✅ HITL gate | Export blocked until named human approves |
| ✅ AI disclaimer | Displayed throughout — professional validation required |

---

## ⚠️ Known Limitations

1. Emission factors are representative values (GHG Protocol 2023); not jurisdiction-specific
2. Scope 3 coverage is partial (business travel, waste, procurement only)
3. RAG quality depends on knowledge base richness; built-in fallback is provided
4. Net-zero projections are planning estimates, not regulatory-grade calculations
5. LLM responses require `GOOGLE_API_KEY` — tools and validators work without it

---

## 🔮 Future Improvements

- IoT sensor integration for real-time emissions tracking
- Expanded Scope 3 categories (supply chain, capital goods)
- LangGraph state machine for more complex agent routing
- GRI/SASB/TCFD export format support
- Carbon credit marketplace integration
- Multi-tenant authentication

---

## 📚 Knowledge Sources

- [GHG Protocol Corporate Standard](https://ghgprotocol.org/)
- [IPCC AR6 Working Group III — Mitigation](https://www.ipcc.ch/report/ar6/wg3/)
- [Science Based Targets initiative (SBTi)](https://sciencebasedtargets.org/)
- [IEA Global EV Outlook](https://www.iea.org/reports/global-ev-outlook-2024)

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 👤 Author

IBM SkillsBuild Academic Program — Gartner Capstone 2026
GitHub: [@vignesh2396](https://github.com/vignesh2396)
