"""
LangChain tools for RAG-powered search over the company knowledge base.

These run in the main FastAPI process (not an MCP subprocess) because ChromaDB
uses SQLite under the hood and Windows file locking makes cross-process access
unreliable.  The other five MCP servers simulate external SaaS APIs over stdio;
the knowledge base is an internal resource, so a direct tool is the right fit.
"""

from langchain_core.tools import tool
from knowledge.vector_store import get_vectorstore

# Lazy singleton — created on first tool call, reused after that
_vs = None


def _get_vs():
    global _vs
    if _vs is None:
        _vs = get_vectorstore()
    return _vs


@tool
def search_company_knowledge(query: str, category: str = "all") -> str:
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
    vs = _get_vs()

    where_filter = None
    if category and category != "all":
        where_filter = {"category": category}

    try:
        results = vs.similarity_search_with_score(
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
        relevance = round((1 - score) * 100, 1)
        lines.append(f"[{i}] {source}  (relevance: {relevance}%)")
        lines.append(doc.page_content.strip())
        lines.append("")

    return "\n".join(lines)


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
