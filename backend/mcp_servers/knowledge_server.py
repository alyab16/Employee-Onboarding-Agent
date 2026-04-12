"""
FastMCP server providing RAG-powered search over Acme Corp's internal knowledge base.
Uses ChromaDB (pre-built by main.py at startup) for semantic retrieval.
Run standalone:  python mcp_servers/knowledge_server.py

NOTE: Tools are async — this avoids the httpx/ProactorEventLoop deadlock that occurs
when OpenAIEmbeddings makes blocking HTTP calls from a thread executor inside FastMCP.
"""

import os
import sys
import logging
from pathlib import Path

# Suppress ChromaDB telemetry before any chromadb import.
# Any stray stdout output corrupts the MCP stdio JSON-RPC protocol.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP

mcp = FastMCP("Knowledge Base")

CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"

# Lazy-loaded on first tool call
_vectorstore = None


def _get_vectorstore():
    """Load the ChromaDB collection. Called once; result cached in module global."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    from langchain_chroma import Chroma

    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            timeout=30,
            max_retries=2,
        )
    else:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(
            model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    _vectorstore = Chroma(
        persist_directory=str(CHROMA_PATH),
        embedding_function=embeddings,
        collection_name="company_knowledge",
    )
    return _vectorstore


@mcp.tool()
async def search_company_knowledge(query: str, category: str = "all") -> str:
    """
    Search Acme Corp's internal knowledge base using semantic similarity.
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
    try:
        vs = _get_vectorstore()
    except Exception as exc:
        return f"Knowledge base initialization error: {exc}"

    where_filter = None
    if category and category != "all":
        where_filter = {"category": category}

    try:
        # Use async search — avoids blocking the event loop with synchronous HTTP calls
        results = await vs.asimilarity_search_with_score(
            query,
            k=4,
            filter=where_filter,
        )
    except Exception as exc:
        return f"Knowledge base search error: {exc}"

    if not results:
        return f"No relevant information found for: '{query}'"

    lines = [f"Knowledge Base — Results for: \"{query}\"\n"]
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown").replace("_", " ").title()
        relevance = round(max(0, 1 / (1 + score)) * 100, 1)  # L2 distance → relevance %
        lines.append(f"[{i}] {source}  (relevance: {relevance}%)")
        lines.append(doc.page_content.strip())
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def list_knowledge_sources() -> str:
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


if __name__ == "__main__":
    mcp.run()
