"""
LangChain tools for RAG-powered search over the company knowledge base.

Production RAG patterns:
  1. Cosine similarity  — ChromaDB collection configured with hnsw:space=cosine
  2. Contextual chunking — each chunk is prefixed with doc title + section header
  3. Hybrid search       — BM25 keyword + vector semantic, merged via Reciprocal
     Rank Fusion (EnsembleRetriever with 0.5/0.5 weighting)

These run in the main FastAPI process (not an MCP subprocess) because ChromaDB
uses SQLite under the hood and Windows file locking makes cross-process access
unreliable.
"""

from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from knowledge.vector_store import get_vectorstore, get_bm25_docs

# Lazy singletons — built on first tool call, reused after that
_hybrid_retriever = None
_vector_store = None


def _get_hybrid_retriever(where_filter: dict | None = None):
    """
    Build an EnsembleRetriever that merges:
      - BM25 (keyword exact-match, good for names/acronyms/IDs)
      - ChromaDB vector search (semantic similarity)
    using Reciprocal Rank Fusion with equal weighting.
    """
    global _hybrid_retriever, _vector_store

    # Always rebuild if there's a category filter (filter changes per query)
    if _hybrid_retriever is not None and where_filter is None:
        return _hybrid_retriever

    # Vector retriever
    if _vector_store is None:
        _vector_store = get_vectorstore()

    search_kwargs: dict = {"k": 4}
    if where_filter:
        search_kwargs["filter"] = where_filter

    vector_retriever = _vector_store.as_retriever(search_kwargs=search_kwargs)

    # BM25 retriever over the same chunks
    bm25_docs = get_bm25_docs()

    # If category filter, narrow BM25 docs to matching category too
    if where_filter and "category" in where_filter:
        cat = where_filter["category"]
        bm25_docs = [d for d in bm25_docs if d.metadata.get("category") == cat]

    bm25_retriever = BM25Retriever.from_documents(bm25_docs, k=4)

    # Reciprocal Rank Fusion — equal weight to keyword and semantic
    ensemble = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.5, 0.5],
    )

    # Cache only the unfiltered version
    if where_filter is None:
        _hybrid_retriever = ensemble

    return ensemble


def _format_results(query: str, docs: list[Document]) -> str:
    """Format retrieved documents into a readable string for the agent."""
    if not docs:
        return f"No relevant information found for: '{query}'"

    # Deduplicate by page_content (BM25 and vector may return the same chunk)
    seen: set[str] = set()
    unique_docs: list[Document] = []
    for doc in docs:
        content_key = doc.page_content.strip()
        if content_key not in seen:
            seen.add(content_key)
            unique_docs.append(doc)

    lines = [
        f"Knowledge Base — Results for: \"{query}\"",
        f"(hybrid search: BM25 keyword + vector semantic, {len(unique_docs)} results)\n",
    ]
    for i, doc in enumerate(unique_docs, 1):
        doc_title = doc.metadata.get("doc_title", "")
        section = doc.metadata.get("section", "")
        source = doc.metadata.get("source", "unknown").replace("_", " ").title()

        # Build a source label
        label = source
        if section:
            label = f"{source} > {section}"

        lines.append(f"[{i}] {label}")
        lines.append(doc.page_content.strip())
        lines.append("")

    return "\n".join(lines)


@tool
def search_company_knowledge(query: str, category: str = "all") -> str:
    """
    Search Acme Corp's internal knowledge base using hybrid retrieval
    (BM25 keyword search + vector semantic search with Reciprocal Rank Fusion).

    Use this to answer employee questions about company policies, benefits,
    security guidelines, and role-specific onboarding information.

    Args:
        query: The question or topic to search for (natural language).
        category: Optional filter — one of: hr, it, engineering, sales, marketing, all.

    Examples:
        search_company_knowledge("What is the PTO policy for L3 employees?")
        search_company_knowledge("code review process", category="engineering")
        search_company_knowledge("401k matching", category="hr")
    """
    where_filter = None
    if category and category != "all":
        where_filter = {"category": category}

    try:
        retriever = _get_hybrid_retriever(where_filter)
        docs = retriever.invoke(query)
    except Exception as exc:
        return f"Knowledge base search error: {exc}"

    return _format_results(query, docs)


@tool
def list_knowledge_sources() -> str:
    """
    List all available knowledge base documents and their categories.
    Use this to understand what topics are covered before searching.
    """
    sources = [
        ("hr_policy",          "hr",          "PTO, remote work, parental leave, performance reviews, expenses"),
        ("code_of_conduct",    "hr",          "Values, ethics, conflicts of interest, anti-harassment, reporting"),
        ("benefits_guide",     "hr",          "Health insurance, 401k, equity/RSUs, wellness stipend, perks"),
        ("it_security_policy", "it",          "Passwords, MFA, devices, data classification, phishing, VPN"),
        ("engineering_guide",  "engineering", "Dev setup, git workflow, code review, testing, deployments, on-call"),
        ("sales_guide",        "sales",       "Sales process, CRM hygiene, quota, territory, key contacts"),
        ("marketing_guide",    "marketing",   "Brand guidelines, campaign process, analytics, content calendar"),
    ]

    lines = ["Knowledge Base — Available Documents\n"]
    for name, category, topics in sources:
        lines.append(f"  [{category.upper()}] {name.replace('_', ' ').title()}")
        lines.append(f"           Topics: {topics}")
    lines.append(
        "\nUse search_company_knowledge(query, category=...) to retrieve relevant sections."
    )
    return "\n".join(lines)
