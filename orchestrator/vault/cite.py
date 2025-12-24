from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Citation:
    doc_id: str
    title: str
    path: str
    quote: str


def format_citations(citations: List[Citation], *, no_citations_reason: Optional[str] = None) -> str:
    """
    Format a citations section that agents must attach to ADRs/specs/implementations.

    If no citations are provided, a no_citations_reason must be supplied to emit a
    “NO_CITATIONS: reason” entry, enforcing the repository rule.
    """
    lines = ["## Citations"]
    if citations:
        for c in citations:
            quote = c.quote.strip().replace("\n", " ")
            if len(quote) > 200:
                quote = quote[:200] + "..."
            lines.append(f"- [{c.doc_id}] {c.title} (vault://{c.path}) — “{quote}”")
        return "\n".join(lines)

    if not no_citations_reason:
        raise ValueError("no_citations_reason is required when no citations are supplied")

    lines.append(f"- NO_CITATIONS: {no_citations_reason}")
    return "\n".join(lines)
