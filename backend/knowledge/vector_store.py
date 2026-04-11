"""
ChromaDB vector store builder.
Called once at application startup — rebuilds only when knowledge_docs change.
"""

import os
import hashlib
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.logger import get_logger

logger = get_logger("vector_store")

DOCS_PATH = Path(__file__).parent.parent / "knowledge_docs"
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
HASH_FILE = CHROMA_PATH / ".docs_hash"


def _get_embeddings():
    """Return embeddings — OpenAI if key present, Ollama nomic-embed-text otherwise."""
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import OpenAIEmbeddings
        logger.info("vector_store.embeddings", provider="openai", model="text-embedding-3-small")
        return OpenAIEmbeddings(model="text-embedding-3-small")
    else:
        from langchain_ollama import OllamaEmbeddings
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        logger.info("vector_store.embeddings", provider="ollama", model=embed_model)
        return OllamaEmbeddings(model=embed_model, base_url=ollama_base)


def _docs_hash() -> str:
    """Stable hash of all document file contents — used to detect changes."""
    h = hashlib.sha256()
    for f in sorted(DOCS_PATH.glob("*.md")):
        h.update(f.read_bytes())
    return h.hexdigest()


def _needs_rebuild() -> bool:
    if not CHROMA_PATH.exists():
        return True
    if not HASH_FILE.exists():
        return True
    return HASH_FILE.read_text().strip() != _docs_hash()


def init_vector_store() -> None:
    """
    Index all markdown documents in knowledge_docs/ into ChromaDB.
    Skips rebuild if documents haven't changed since last run.
    """
    if not _needs_rebuild():
        logger.info("vector_store.skip_rebuild", reason="docs unchanged")
        return

    logger.info("vector_store.building", docs_path=str(DOCS_PATH))
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    # Load and tag each document with metadata
    raw_docs: list[Document] = []
    for doc_file in sorted(DOCS_PATH.glob("*.md")):
        content = doc_file.read_text(encoding="utf-8")
        raw_docs.append(Document(
            page_content=content,
            metadata={
                "source": doc_file.stem,
                "filename": doc_file.name,
                "category": _infer_category(doc_file.stem),
            },
        ))
    logger.info("vector_store.loaded", doc_count=len(raw_docs))

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(raw_docs)
    logger.info("vector_store.chunked", chunk_count=len(chunks))

    # Build and persist
    embeddings = _get_embeddings()
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
        collection_name="company_knowledge",
    )

    # Save hash to skip rebuild next time
    HASH_FILE.write_text(_docs_hash())
    logger.info("vector_store.ready", chunks=len(chunks))


def _infer_category(stem: str) -> str:
    mapping = {
        "hr_policy": "hr",
        "code_of_conduct": "hr",
        "benefits_guide": "hr",
        "it_security_policy": "it",
        "engineering_guide": "engineering",
        "sales_guide": "sales",
        "marketing_guide": "marketing",
    }
    return mapping.get(stem, "general")
