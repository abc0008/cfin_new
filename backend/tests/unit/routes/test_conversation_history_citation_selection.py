from types import SimpleNamespace

from app.routes.conversation import _normalize_message_citations_for_markers


def _citation(
    citation_id: str,
    cited_text: str,
    *,
    document_id: str = "doc-1",
    start_page_number: int = 1,
    section: str | None = None,
):
    return SimpleNamespace(
        id=citation_id,
        document_id=document_id,
        start_page_number=start_page_number,
        page=start_page_number,
        section=section,
        cited_text=cited_text,
        text=cited_text,
    )


def test_normalize_citations_deduplicates_and_trims_to_marker_count():
    citations = [
        _citation("cite-table-1", "(Loss) income from unconsolidated affiliates ... (1,095)"),
        _citation("cite-table-dup", "(Loss) income from unconsolidated affiliates ... (1,095)"),
        _citation("cite-net-sales", "Net Sales of $997.7 million versus $897.0 million"),
    ]

    selected = _normalize_message_citations_for_markers(citations, "Answer text [1]")

    assert [c.id for c in selected] == ["cite-table-1"]


def test_normalize_citations_keeps_unique_order_when_no_markers():
    citations = [
        _citation("cite-a", "Operating income 210,006"),
        _citation("cite-a-dup", "Operating income 210,006"),
        _citation("cite-b", "Interest income 14,383"),
    ]

    selected = _normalize_message_citations_for_markers(citations, "Answer without inline markers")

    assert [c.id for c in selected] == ["cite-a", "cite-b"]


def test_normalize_citations_keeps_distinct_marker_sections_for_same_table_block():
    table_text = "MUELLER INDUSTRIES ... Net sales 997,745 ... Operating income 210,006"
    citations = [
        _citation("cite-marker-1", table_text, start_page_number=2, section="1"),
        _citation("cite-marker-2", table_text, start_page_number=2, section="2"),
    ]

    selected = _normalize_message_citations_for_markers(
        citations,
        "Net sales = $997,745 [1]; Operating income = $210,006 [2]",
    )

    assert [c.id for c in selected] == ["cite-marker-1", "cite-marker-2"]
