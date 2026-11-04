"""
rag/embeddings.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  RAG document ingestion pipeline.
          Loads PDF sustainability documents (GHG Protocol, IPCC AR6, SBTi),
          chunks them, generates embeddings, and stores in an InMemoryVectorStore.

          Uses langchain_core.vectorstores.InMemoryVectorStore — no external
          vector DB dependency (avoids chromadb version conflicts).

Responsible AI note:
    - Only publicly available, authoritative sustainability documents are used.
    - No personal or proprietary data is embedded.
    - Sources are always disclosed alongside any retrieved content.

Dependencies: langchain-core, langchain-community, langchain-google-genai, pypdf
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from utils.logger import get_logger

log = get_logger("RAGEmbeddings")

# ── Configuration ─────────────────────────────────────────────────────────────
DOCUMENTS_DIR   = Path(__file__).parent / "documents"
EMBEDDING_MODEL = "models/text-embedding-004"

# Chunk settings: 1000 chars with 200-char overlap for context continuity
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200


def _get_embedding_function() -> GoogleGenerativeAIEmbeddings:
    """Return a configured Google embedding function."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
    )


def build_knowledge_base(
    documents_dir: Path = DOCUMENTS_DIR,
) -> InMemoryVectorStore:
    """
    Build an InMemoryVectorStore from PDF documents (or built-in fallback).

    On first call: loads PDFs → chunks → embeds → stores in memory.
    The store is held in the module-level singleton in retriever.py.

    Args:
        documents_dir: Directory containing PDF knowledge sources.

    Returns:
        An InMemoryVectorStore instance ready for similarity search.
    """
    embedding_fn = _get_embedding_function()

    # ── Load PDF Documents ────────────────────────────────────────────────
    pdf_files = list(documents_dir.glob("*.pdf"))
    if not pdf_files:
        log.info(
            "No PDF documents found in rag/documents/. Using built-in fallback knowledge base.",
            extra={"action": "rag_no_docs"}
        )
        return _build_fallback_knowledge_base(embedding_fn)

    all_docs = []
    for pdf_path in pdf_files:
        log.info(f"Loading document: {pdf_path.name}", extra={"action": "rag_load_doc"})
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages  = loader.load()
            for page in pages:
                page.metadata["source"] = pdf_path.name
            all_docs.extend(pages)
        except Exception as e:
            log.warning(
                f"Failed to load {pdf_path.name}: {e}",
                extra={"action": "rag_load_error", "warning": str(e)}
            )

    if not all_docs:
        log.warning("All PDF loads failed. Using fallback.", extra={"action": "rag_fallback"})
        return _build_fallback_knowledge_base(embedding_fn)

    # ── Chunk Documents ───────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(all_docs)
    log.info(
        f"Created {len(chunks)} chunks from {len(pdf_files)} documents",
        extra={"action": "rag_chunked", "chunk_count": len(chunks)}
    )

    # ── Embed & Store ─────────────────────────────────────────────────────
    vectorstore = InMemoryVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_fn,
    )
    log.info(
        "InMemoryVectorStore knowledge base built",
        extra={"action": "rag_built", "doc_count": len(pdf_files)}
    )
    return vectorstore


def _build_fallback_knowledge_base(
    embedding_fn: GoogleGenerativeAIEmbeddings,
) -> InMemoryVectorStore:
    """
    Build a minimal fallback knowledge base from embedded text strings
    when no PDF documents are available. Contains core GHG Protocol guidance.
    """
    from langchain_core.documents import Document

    fallback_docs = [
        Document(
            page_content=(
                "The GHG Protocol Corporate Standard requires organizations to account for "
                "emissions in three scopes: Scope 1 (direct emissions from owned/controlled "
                "sources), Scope 2 (indirect emissions from purchased electricity, steam, "
                "heat or cooling), and Scope 3 (all other indirect emissions in value chain). "
                "Switching to renewable electricity (100% renewable energy certificates) "
                "eliminates Scope 2 electricity emissions entirely."
            ),
            metadata={"source": "GHG Protocol Corporate Standard (built-in)"}
        ),
        Document(
            page_content=(
                "Key decarbonization strategies for electricity emissions include: "
                "1) Power Purchase Agreements (PPAs) for renewable energy — eliminates Scope 2 emissions, "
                "typical cost: $0–5/MWh premium, feasibility: High. "
                "2) On-site solar PV installation — reduces Scope 2 by 20-60%, "
                "payback period: 5-8 years, feasibility: High for manufacturing. "
                "3) Energy efficiency improvements (LED lighting, HVAC optimization) — "
                "reduces electricity consumption 10-30%, low cost, High feasibility."
            ),
            metadata={"source": "GHG Protocol / IEA Net Zero Pathways (built-in)"}
        ),
        Document(
            page_content=(
                "Business travel emission reduction strategies: "
                "1) Virtual meeting policy — replace non-essential air travel with video conferencing. "
                "Estimated reduction: 40-70% of business travel emissions. Cost: minimal. "
                "2) Sustainable Travel Policy — mandate economy class (lower per-seat emissions), "
                "prefer rail over short-haul flights. Reduction: 15-25%. "
                "3) Carbon offsetting for unavoidable flights — high-quality verified offsets "
                "(Gold Standard / VCS). Cost: $10-25/tCO2e."
            ),
            metadata={"source": "IPCC AR6 Mitigation Pathways (built-in)"}
        ),
        Document(
            page_content=(
                "Waste reduction and circular economy strategies: "
                "1) Waste-to-energy programs — divert organic waste from landfill. "
                "Reduces Scope 3 waste emissions by 50-80%. "
                "2) Recycling and composting programs — reduce landfill waste. "
                "3) Procurement policies prioritizing recycled content — "
                "reduces embodied carbon in purchased goods. "
                "Science Based Targets initiative (SBTi) recommends a 50% absolute reduction "
                "by 2030 and net zero by 2050 aligned with 1.5 degrees C pathway."
            ),
            metadata={"source": "SBTi Net-Zero Standard (built-in)"}
        ),
        Document(
            page_content=(
                "Fleet and logistics decarbonization: "
                "1) Electrification of company fleet — replace diesel vehicles with EVs. "
                "Eliminates Scope 1 mobile combustion emissions entirely. "
                "Upfront cost: $10,000-30,000 per vehicle premium; 5-7 year payback. "
                "2) Driver behavior training — eco-driving reduces fuel use by 5-15%. "
                "3) Route optimization software — reduces total km driven by 10-20%. "
                "4) Hydrogen fuel cell vehicles for heavy logistics (longer horizon, 2028+)."
            ),
            metadata={"source": "IEA Global EV Outlook / GHG Protocol (built-in)"}
        ),
        Document(
            page_content=(
                "Stationary combustion and natural gas decarbonization: "
                "1) Heat pump replacement for gas heating — eliminates Scope 1 gas boiler emissions. "
                "Feasibility: High for commercial buildings. Cost: $15,000-50,000 per unit. "
                "2) Renewable natural gas (biogas/biomethane) — reduce Scope 1 combustion emissions by 80-100%. "
                "3) Building insulation and energy management systems — reduce heating demand 20-40%."
            ),
            metadata={"source": "IEA Energy Efficiency Report / GHG Protocol (built-in)"}
        ),
    ]

    vectorstore = InMemoryVectorStore.from_documents(
        documents=fallback_docs,
        embedding=embedding_fn,
    )
    log.info(
        f"Fallback knowledge base built with {len(fallback_docs)} built-in documents",
        extra={"action": "rag_fallback_built"}
    )
    return vectorstore
