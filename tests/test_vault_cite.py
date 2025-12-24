from orchestrator.vault import Citation, format_citations


def test_format_citations_includes_bullets_and_truncates() -> None:
    citation = Citation(
        doc_id="abc123",
        title="Design Doc",
        path="sources/doc.md",
        quote="A" * 210,
    )
    rendered = format_citations([citation])
    assert "vault://sources/doc.md" in rendered
    assert "abc123" in rendered
    assert rendered.count("...") == 1


def test_format_citations_requires_reason_when_empty() -> None:
    rendered = format_citations([], no_citations_reason="No references required")
    assert "NO_CITATIONS: No references required" in rendered
