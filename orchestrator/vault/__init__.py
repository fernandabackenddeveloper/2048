"""Lightweight knowledge vault for ingest, indexing, retrieval, and citations."""

from orchestrator.vault.vault import Vault
from orchestrator.vault.ingest import add_local_file, add_note
from orchestrator.vault.indexer import rebuild_index
from orchestrator.vault.retrieval import retrieve, RetrievedDoc
from orchestrator.vault.cite import Citation, format_citations

__all__ = [
    "Vault",
    "add_local_file",
    "add_note",
    "rebuild_index",
    "retrieve",
    "RetrievedDoc",
    "Citation",
    "format_citations",
]
