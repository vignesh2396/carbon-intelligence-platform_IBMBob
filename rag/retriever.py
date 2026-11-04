"""
rag/retriever.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  RAG retrieval interface. Executes similarity searches against the
          InMemoryVectorStore knowledge base and returns structured, sourced results.

          Explainability: Every retrieved result includes the source document
          and relevance score so the UI can show users exactly where the
          AI's recommendations come from.

Dependencies: langchain-core, rag/embeddings.py
"""

from __future__ import annotations

import os
from typing import Any, Optional

from langchain_core.vectorstores import InMemoryVectorStore

from rag.embeddings import build_knowledge_base
from utils.logger import get_logger

log = get_logger("RAGRetriever")

CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.6"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# Singleton: build/load the vector store once per application session
_vectorstore: Optional[InMemoryVectorStore] = None


def get_vectorstore() -> InMemoryVectorStore:
    """Return the singleton InMemoryVectorStore (lazy-initialized)."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_knowledge_base()
    return _vectorstore


def retrieve_reduction_strategies(
    hotspot_description: str,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant decarbonization strategy knowledge for a given hotspot.

    Args:
        hotspot_description:  Natural language description of the emission hotspot.
        top_k:                Number of top results to return.

    Returns:
        List of retrieved knowledge chunks:
        [{
            "content":     str,    # The relevant text
            "source":      str,    # Source document name
            "score":       float,  # Relevance score (0–1; higher is more relevant)
            "confidence":  str,    # "High" | "Medium" | "Low"
        }]

    Responsible AI: Confidence indicator is always shown to the user.
                    Low confidence results include a disclaimer.
    """
    try:
        vs = get_vectorstore()
    except Exception as e:
        log.warning(
            f"Vector store unavailable: {e}. RAG retrieval skipped.",
            extra={"action": "rag_unavailable", "warning": str(e)}
        )
        return []

    query = f"Carbon emission reduction strategies for: {hotspot_description}"

    try:
        # InMemoryVectorStore similarity_search_with_score returns (doc, score) tuples
        # where score is the raw distance (lower = more similar for L2, higher for cosine)
        results_with_scores = vs.similarity_search_with_score(query, k=top_k)
    except Exception as e:
        log.warning(f"RAG search failed: {e}", extra={"action": "rag_search_error"})
        return []

    # Determine score orientation: InMemoryVectorStore cosine similarity → higher is better
    # Scores are already in [0, 1] for cosine similarity
    structured_results: list[dict[str, Any]] = []
    for doc, score in results_with_scores:
        score = max(0.0, min(1.0, float(score)))

        if score >= 0.75:
            confidence = "High"
        elif score >= CONFIDENCE_THRESHOLD:
            confidence = "Medium"
        else:
            confidence = "Low"

        result = {
            "content":    doc.page_content,
            "source":     doc.metadata.get("source", "Unknown source"),
            "score":      round(score, 3),
            "confidence": confidence,
        }
        structured_results.append(result)

    log.info(
        f"RAG retrieved {len(structured_results)} chunks for: '{hotspot_description[:60]}'",
        extra={
            "action":       "rag_retrieved",
            "query":        hotspot_description[:100],
            "result_count": len(structured_results),
            "confidence":   [r["confidence"] for r in structured_results],
        }
    )
    return structured_results


def format_rag_context(retrieved_chunks: list[dict[str, Any]]) -> str:
    """
    Format retrieved RAG chunks into a single context string for LLM prompting.
    Includes source attribution for explainability.
    """
    if not retrieved_chunks:
        return "No knowledge base documents retrieved for this query."

    parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        parts.append(
            f"[Source {i}: {chunk['source']} | Relevance: {chunk['confidence']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)
