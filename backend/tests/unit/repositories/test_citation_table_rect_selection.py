from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from models.database_models import Citation, Message, MessageCitation
from repositories.document_repository import DocumentRepository


class _TestRepo(DocumentRepository):
    def __init__(self, pdf_path: Path):
        super().__init__(
            db=None,
            storage_service=SimpleNamespace(get_file_path=lambda _file_id: str(pdf_path)),
        )
        self._pdf_path = str(pdf_path)

    def get_document_file_path(self, document_id: str) -> str:
        return self._pdf_path


def _make_citation(**overrides) -> Citation:
    payload = {
        "id": "test-citation-id",
        "document_id": "test-document-id",
        "type": "page_location",
        "page": 1,
        "text": "table citation",
        "cited_text": "Metric 2024 2023\nNet sales 500 400\nOperating income 300 500",
        "display_text": "Net sales: 500",
        "searchable_text": None,
        "document_title": "Test Document",
        "start_page_number": 1,
        "end_page_number": 1,
        "rects": "[]",
        "highlight_id": "test-citation-id",
    }
    payload.update(overrides)
    return Citation(**payload)


def _extract_rect_text(pdf_path: Path, rect: dict) -> str:
    with fitz.open(str(pdf_path)) as doc:
        page = doc.load_page(rect["pageNumber"] - 1)
        x1 = min(float(rect["x1"]), float(rect["x2"]))
        x2 = max(float(rect["x1"]), float(rect["x2"]))
        y1 = float(rect["y1"])
        y2 = float(rect["y2"])
        page_height = float(page.rect.height)

        clip_top_left = fitz.Rect(x1, min(y1, y2), x2, max(y1, y2))
        text_top_left = " ".join(page.get_text("text", clip=clip_top_left).split())

        y_a = page_height - y1
        y_b = page_height - y2
        clip_pdfjs = fitz.Rect(x1, min(y_a, y_b), x2, max(y_a, y_b))
        text_pdfjs = " ".join(page.get_text("text", clip=clip_pdfjs).split())

        def _score_text(value: str) -> tuple[int, int]:
            return (1 if any(ch.isdigit() for ch in value) else 0, len(value))

        return text_pdfjs if _score_text(text_pdfjs) >= _score_text(text_top_left) else text_top_left


@pytest.mark.unit
def test_prefers_row_and_column_aligned_table_cell(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    target_rect = {
        "x1": 100.0,
        "y1": 200.0,
        "x2": 130.0,
        "y2": 212.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    false_match_rect = {
        "x1": 200.0,
        "y1": 230.0,
        "x2": 230.0,
        "y2": 242.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = cited_text.replace("$", "").replace(",", "").strip()
        if normalized in {"500", "(500)", "-500"}:
            return [target_rect, false_match_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 165, 130, 175, "2024", 0, 0, 0),
                (205, 165, 230, 175, "2023", 0, 0, 1),
                (40, 200, 60, 212, "Net", 1, 0, 0),
                (62, 200, 95, 212, "sales", 1, 0, 1),
                (100, 200, 130, 212, "500", 1, 0, 2),
                (200, 200, 230, 212, "400", 1, 0, 3),
                (40, 230, 95, 242, "Operating", 2, 0, 0),
                (98, 230, 135, 242, "income", 2, 0, 1),
                (160, 230, 190, 242, "300", 2, 0, 2),
                (200, 230, 230, 242, "500", 2, 0, 3),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation()
    api_citation = repo.citation_to_api_schema(citation)

    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["pageNumber"] == 1
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_uses_searchable_year_hint_to_pick_correct_table_column(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_column_rect = {
        "x1": 100.0,
        "y1": 200.0,
        "x2": 130.0,
        "y2": 212.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 200.0,
        "x2": 230.0,
        "y2": 212.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = cited_text.replace("$", "").replace(",", "").strip()
        if normalized in {"500", "(500)", "-500"}:
            return [wrong_column_rect, target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 165, 130, 175, "2024", 0, 0, 0),
                (205, 165, 230, 175, "2023", 0, 0, 1),
                (40, 200, 60, 212, "Net", 1, 0, 0),
                (62, 200, 95, 212, "sales", 1, 0, 1),
                (100, 200, 130, 212, "500", 1, 0, 2),
                (200, 200, 230, 212, "500", 1, 0, 3),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text="Metric 2024 2023\nNet sales 500 500",
        display_text="Net sales: 500",
        searchable_text="2023.",
    )
    api_citation = repo.citation_to_api_schema(citation)

    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_mueller_table_citation_targets_numeric_cell_not_footnote():
    repo_root = Path(__file__).resolve().parents[4]
    pdf_path = repo_root / "ExampleDocs" / "Mueller Industries Earnings Release.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Missing sample PDF: {pdf_path}")

    repo = _TestRepo(pdf_path)
    citation = _make_citation(
        id="mueller-row-col-test",
        document_id="mueller-doc",
        page=3,
        start_page_number=3,
        end_page_number=3,
        text="(Loss) income row",
        cited_text=(
            "(Loss) income from unconsolidated\n"
            "affiliates, net of foreign tax (1,095) 715 (9,102) (269)\n"
            "Consolidated net income 163"
        ),
        display_text="(Loss) income from unconsolidated: ,",
        searchable_text=None,
        highlight_id="mueller-row-col-test",
    )

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1

    rect = api_citation["rects"][0]
    text = _extract_rect_text(pdf_path, rect)
    assert "1,095" in text
    assert text not in {"(1)", "1"}


@pytest.mark.unit
def test_uses_linked_message_marker_context_to_select_correct_table_value(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_value_rect = {
        "x1": 100.0,
        "y1": 200.0,
        "x2": 130.0,
        "y2": 212.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 200.0,
        "x2": 230.0,
        "y2": 212.0,
        "width": 30.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = cited_text.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
        if normalized in {"1095", "-1095"}:
            return [wrong_value_rect]
        if normalized in {"715"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 165, 130, 175, "2024", 0, 0, 0),
                (205, 165, 230, 175, "2023", 0, 0, 1),
                (40, 200, 60, 212, "Loss", 1, 0, 0),
                (62, 200, 95, 212, "income", 1, 0, 1),
                (100, 200, 130, 212, "(1,095)", 1, 0, 2),
                (200, 200, 230, 212, "715", 1, 0, 3),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "(Loss) income from unconsolidated affiliates, net of foreign tax (1,095) 715"
        ),
        display_text="(Loss) income from unconsolidated: ,",
        searchable_text=None,
    )
    linked_message = Message(
        id="message-1",
        conversation_id="conversation-1",
        role="assistant",
        content="For the quarter ended July 1, 2023, the value was $715. [1]",
    )
    citation.messages = [
        MessageCitation(
            message_id="message-1",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_ignores_low_information_searchable_token_and_uses_row_column_context(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_row_rect = {
        "x1": 300.0,
        "y1": 170.0,
        "x2": 350.0,
        "y2": 182.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 230.0,
        "x2": 240.0,
        "y2": 242.0,
        "width": 40.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
        )
        if normalized == "29":
            return [wrong_row_rect]
        if normalized in {"997745", "896984"}:
            return [wrong_row_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 170, 70, 182, "Net", 1, 0, 0),
                (72, 170, 95, 182, "sales", 1, 0, 1),
                (300, 170, 350, 182, "997,745", 1, 0, 2),
                (200, 170, 250, 182, "896,984", 1, 0, 3),
                (40, 230, 75, 242, "Other", 2, 0, 0),
                (77, 230, 115, 242, "(expense)", 2, 0, 1),
                (117, 230, 150, 242, "income,", 2, 0, 2),
                (152, 230, 170, 242, "net", 2, 0, 3),
                (100, 230, 150, 242, "(1,356)", 2, 0, 4),
                (200, 230, 240, 242, "1,841", 2, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text=(
            "MUELLER INDUSTRIES, INC. CONDENSED CONSOLIDATED STATEMENTS OF INCOME "
            "For the Quarter Ended June 29, 2024 July 1, 2023"
        ),
        searchable_text="29.",
    )
    linked_message = Message(
        id="message-2",
        conversation_id="conversation-2",
        role="assistant",
        content=(
            "For the quarter ended July 1, 2023, Other (expense) income, net was "
            "$1,841 thousand. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-2",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_uses_markerless_message_context_to_avoid_header_value_match(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_rect = {
        "x1": 300.0,
        "y1": 190.0,
        "x2": 350.0,
        "y2": 202.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"997745"}:
            return [wrong_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 190, 70, 202, "Net", 1, 0, 0),
                (72, 190, 98, 202, "sales", 1, 0, 1),
                (300, 190, 350, 202, "997,745", 1, 0, 2),
                (200, 190, 250, 202, "896,984", 1, 0, 3),
                (40, 250, 75, 262, "Other", 2, 0, 0),
                (77, 250, 116, 262, "(expense)", 2, 0, 1),
                (118, 250, 151, 262, "income,", 2, 0, 2),
                (153, 250, 171, 262, "net", 2, 0, 3),
                (100, 250, 151, 262, "(1,356)", 2, 0, 4),
                (200, 250, 245, 262, "1,841", 2, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "MUELLER INDUSTRIES, INC.\n"
            "CONDENSED CONSOLIDATED STATEMENTS OF INCOME\n"
            "(In thousands, except per share data)\n"
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text="(In thousands, except per share data): 29,",
        searchable_text="29",
    )
    linked_message = Message(
        id="message-markerless-1",
        conversation_id="conversation-markerless-1",
        role="assistant",
        content=(
            "# Financial Analysis: Mueller Industries Q2 2024 Earnings Report\n\n"
            "For the quarter ended July 1, 2023, Mueller Industries reported Other "
            "(expense) income, net of $1,841 thousand. It's worth noting that in the "
            "most recent quarter ended June 29, 2024, this same line item showed an "
            "expense of $(1,356) thousand."
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-markerless-1",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_uses_multi_marker_message_context_and_avoids_header_phrase_match(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    header_rect = {
        "x1": 320.0,
        "y1": 150.0,
        "x2": 520.0,
        "y2": 162.0,
        "width": 200.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    wrong_numeric_rect = {
        "x1": 300.0,
        "y1": 190.0,
        "x2": 350.0,
        "y2": 202.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"in thousands except per share data"}:
            return [header_rect]
        if normalized in {"997745"}:
            return [wrong_numeric_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (320, 150, 340, 162, "(In", 0, 1, 0),
                (342, 150, 390, 162, "thousands,", 0, 1, 1),
                (392, 150, 430, 162, "except", 0, 1, 2),
                (432, 150, 455, 162, "per", 0, 1, 3),
                (457, 150, 485, 162, "share", 0, 1, 4),
                (487, 150, 520, 162, "data)", 0, 1, 5),
                (40, 190, 70, 202, "Net", 1, 0, 0),
                (72, 190, 98, 202, "sales", 1, 0, 1),
                (300, 190, 350, 202, "997,745", 1, 0, 2),
                (200, 190, 250, 202, "896,984", 1, 0, 3),
                (40, 250, 75, 262, "Other", 2, 0, 0),
                (77, 250, 116, 262, "(expense)", 2, 0, 1),
                (118, 250, 151, 262, "income,", 2, 0, 2),
                (153, 250, 171, 262, "net", 2, 0, 3),
                (100, 250, 151, 262, "(1,356)", 2, 0, 4),
                (200, 250, 245, 262, "1,841", 2, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "(In thousands, except per share data)\n"
            "Net sales 997,745 896,984\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text=(
            "MUELLER INDUSTRIES, INC. CONDENSED CONSOLIDATED STATEMENTS OF INCOME "
            "For the Quarter Ended June 29, 2024 July 1, 2023"
        ),
        searchable_text="29.",
    )
    linked_message = Message(
        id="message-3",
        conversation_id="conversation-3",
        role="assistant",
        content=(
            "For the quarter ended July 1, 2023, the value was $1,841 thousand and "
            "it appears in Other (expense) income, net. [1] [2]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-3",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_uses_marker_index_hint_to_separate_multi_value_row_matches(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    net_sales_rect = {
        "x1": 300.0,
        "y1": 190.0,
        "x2": 350.0,
        "y2": 202.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    operating_income_rect = {
        "x1": 300.0,
        "y1": 250.0,
        "x2": 350.0,
        "y2": 262.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"997745"}:
            return [net_sales_rect]
        if normalized in {"210006"}:
            return [operating_income_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 190, 70, 202, "Net", 1, 0, 0),
                (72, 190, 98, 202, "sales", 1, 0, 1),
                (300, 190, 350, 202, "997,745", 1, 0, 2),
                (200, 190, 250, 202, "896,984", 1, 0, 3),
                (40, 250, 110, 262, "Operating", 2, 0, 0),
                (112, 250, 150, 262, "income", 2, 0, 1),
                (300, 250, 350, 262, "210,006", 2, 0, 2),
                (200, 250, 250, 262, "210,700", 2, 0, 3),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    linked_message = Message(
        id="message-marker-hints",
        conversation_id="conversation-marker-hints",
        role="assistant",
        content=(
            "Net Sales for the quarter ended June 29, 2024 were $997,745. [1] "
            "Operating income for the same quarter was $210,006. [2]"
        ),
    )

    citation_1 = _make_citation(
        id="marker-hint-cite-1",
        highlight_id="marker-hint-cite-1",
        searchable_text="2023.",
        section="1",
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Operating income 210,006 210,700"
        ),
    )
    citation_2 = _make_citation(
        id="marker-hint-cite-2",
        highlight_id="marker-hint-cite-2",
        searchable_text="2023.",
        section="2",
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Operating income 210,006 210,700"
        ),
    )

    citation_1.messages = [
        MessageCitation(
            message_id="message-marker-hints",
            citation_id=str(citation_1.id),
            message=linked_message,
            citation=citation_1,
        )
    ]
    citation_2.messages = [
        MessageCitation(
            message_id="message-marker-hints",
            citation_id=str(citation_2.id),
            message=linked_message,
            citation=citation_2,
        )
    ]

    api_citation_1 = repo.citation_to_api_schema(citation_1)
    api_citation_2 = repo.citation_to_api_schema(citation_2)

    assert len(api_citation_1["rects"]) == 1
    assert len(api_citation_2["rects"]) == 1

    selected_1 = api_citation_1["rects"][0]
    selected_2 = api_citation_2["rects"][0]

    assert selected_1["x1"] == net_sales_rect["x1"]
    assert selected_2["x1"] == operating_income_rect["x1"]
    assert selected_1["y1"] == pytest.approx(800.0 - net_sales_rect["y2"])
    assert selected_2["y1"] == pytest.approx(800.0 - operating_income_rect["y2"])


@pytest.mark.unit
def test_uses_marker_index_hint_for_markerless_assignment_style_answers(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    net_sales_rect = {
        "x1": 300.0,
        "y1": 190.0,
        "x2": 350.0,
        "y2": 202.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    operating_income_rect = {
        "x1": 300.0,
        "y1": 250.0,
        "x2": 350.0,
        "y2": 262.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"997745"}:
            return [net_sales_rect]
        if normalized in {"210006"}:
            return [operating_income_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 190, 70, 202, "Net", 1, 0, 0),
                (72, 190, 98, 202, "sales", 1, 0, 1),
                (300, 190, 350, 202, "997,745", 1, 0, 2),
                (200, 190, 250, 202, "896,984", 1, 0, 3),
                (40, 250, 110, 262, "Operating", 2, 0, 0),
                (112, 250, 150, 262, "income", 2, 0, 1),
                (300, 250, 350, 262, "210,006", 2, 0, 2),
                (200, 250, 250, 262, "210,700", 2, 0, 3),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    linked_message = Message(
        id="message-markerless-assignments",
        conversation_id="conversation-markerless-assignments",
        role="assistant",
        content=(
            "For the quarter ended June 29, 2024: "
            "Net sales = $997,745 Operating income = $210,006"
        ),
    )

    citation_1 = _make_citation(
        id="markerless-assign-cite-1",
        highlight_id="markerless-assign-cite-1",
        searchable_text="29",
        section="1",
        display_text="(In thousands, except per share data): 29,",
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Operating income 210,006 210,700"
        ),
    )
    citation_2 = _make_citation(
        id="markerless-assign-cite-2",
        highlight_id="markerless-assign-cite-2",
        searchable_text="29",
        section="2",
        display_text="(In thousands, except per share data): 29,",
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984\n"
            "Operating income 210,006 210,700"
        ),
    )

    citation_1.messages = [
        MessageCitation(
            message_id="message-markerless-assignments",
            citation_id=str(citation_1.id),
            message=linked_message,
            citation=citation_1,
        )
    ]
    citation_2.messages = [
        MessageCitation(
            message_id="message-markerless-assignments",
            citation_id=str(citation_2.id),
            message=linked_message,
            citation=citation_2,
        )
    ]

    api_citation_1 = repo.citation_to_api_schema(citation_1)
    api_citation_2 = repo.citation_to_api_schema(citation_2)

    assert len(api_citation_1["rects"]) == 1
    assert len(api_citation_2["rects"]) == 1
    assert api_citation_1["rects"][0]["x1"] == net_sales_rect["x1"]
    assert api_citation_2["rects"][0]["x1"] == operating_income_rect["x1"]


@pytest.mark.unit
def test_maps_actual_dollars_message_value_to_thousands_table_cell(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_rect = {
        "x1": 300.0,
        "y1": 190.0,
        "x2": 350.0,
        "y2": 202.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"997745"}:
            return [wrong_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 190, 70, 202, "Net", 1, 0, 0),
                (72, 190, 98, 202, "sales", 1, 0, 1),
                (300, 190, 350, 202, "997,745", 1, 0, 2),
                (200, 190, 250, 202, "896,984", 1, 0, 3),
                (40, 250, 75, 262, "Other", 2, 0, 0),
                (77, 250, 116, 262, "(expense)", 2, 0, 1),
                (118, 250, 151, 262, "income,", 2, 0, 2),
                (153, 250, 171, 262, "net", 2, 0, 3),
                (100, 250, 151, 262, "(1,356)", 2, 0, 4),
                (200, 250, 245, 262, "1,841", 2, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "(In thousands, except per share data)\n"
            "Net sales 997,745 896,984\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text=(
            "MUELLER INDUSTRIES, INC. CONDENSED CONSOLIDATED STATEMENTS OF INCOME "
            "For the Quarter Ended June 29, 2024 July 1, 2023"
        ),
        searchable_text="29.",
    )
    linked_message = Message(
        id="message-4",
        conversation_id="conversation-4",
        role="assistant",
        content=(
            "For the quarter ended July 1, 2023, the amount was $1,841,000 in actual "
            "dollars as the table is reported in thousands. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-4",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_prefers_primary_answer_value_over_for_context_comparison_value(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_rect = {
        "x1": 100.0,
        "y1": 250.0,
        "x2": 150.0,
        "y2": 262.0,
        "width": 50.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"1356", "-1356"}:
            return [wrong_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 250, 75, 262, "Other", 1, 0, 0),
                (77, 250, 116, 262, "(expense)", 1, 0, 1),
                (118, 250, 151, 262, "income,", 1, 0, 2),
                (153, 250, 171, 262, "net", 1, 0, 3),
                (100, 250, 151, 262, "(1,356)", 1, 0, 4),
                (200, 250, 245, 262, "1,841", 1, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text="Other (expense) income, net",
        searchable_text="29.",
    )
    linked_message = Message(
        id="message-5",
        conversation_id="conversation-5",
        role="assistant",
        content=(
            "For the quarter ended July 1, 2023, the value was $1,841 thousand. "
            "For context, in the most recent quarter ended June 29, 2024, the value "
            "was ($1,356) thousand. [1] [2]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-5",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_prefers_primary_answer_value_when_markers_are_trailing_and_sentence_has_comparison_language(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_rect = {
        "x1": 100.0,
        "y1": 250.0,
        "x2": 151.0,
        "y2": 262.0,
        "width": 51.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"1356", "-1356"}:
            return [wrong_rect]
        if normalized in {"1841"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (105, 140, 130, 150, "2024", 0, 0, 0),
                (205, 140, 230, 150, "2023", 0, 0, 1),
                (40, 250, 75, 262, "Other", 1, 0, 0),
                (77, 250, 116, 262, "(expense)", 1, 0, 1),
                (118, 250, 151, 262, "income,", 1, 0, 2),
                (153, 250, 171, 262, "net", 1, 0, 3),
                (100, 250, 151, 262, "(1,356)", 1, 0, 4),
                (200, 250, 245, 262, "1,841", 1, 0, 5),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 July 1, 2023\n"
            "Other (expense) income, net (1,356) 1,841"
        ),
        display_text="Other (expense) income, net",
        searchable_text="(In thousands, except per share data): 29,",
    )
    linked_message = Message(
        id="message-6",
        conversation_id="conversation-6",
        role="assistant",
        content=(
            "For the quarter ended July 1, 2023, Mueller Industries reported Other "
            "(expense) income, net of $1,841 thousand. It's worth noting that this "
            "item has shifted from income in Q2 2023 to expense in Q2 2024, as for "
            "the quarter ended June 29, 2024, the company reported Other (expense) "
            "income, net of ($1,356) thousand, representing a negative swing of "
            "$3,197 thousand year-over-year. [1] [2]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-6",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_uses_nearest_column_term_for_message_hint_without_year_specific_bias(monkeypatch):
    import pdf_processing.rect_finder as rect_finder

    wrong_rect = {
        "x1": 300.0,
        "y1": 250.0,
        "x2": 345.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }
    target_rect = {
        "x1": 200.0,
        "y1": 250.0,
        "x2": 245.0,
        "y2": 262.0,
        "width": 45.0,
        "height": 12.0,
        "pageNumber": 1,
    }

    def fake_find_rects_for_text(*, cited_text: str, **_kwargs):
        normalized = (
            cited_text.replace("$", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .strip()
            .lower()
        )
        if normalized in {"100"}:
            return [wrong_rect]
        if normalized in {"200"}:
            return [target_rect]
        return []

    class _FakePage:
        rect = SimpleNamespace(height=800.0)

        def get_text(self, mode: str):
            assert mode == "words"
            return [
                (205, 140, 230, 150, "2024", 0, 0, 0),
                (305, 140, 330, 150, "2025", 0, 0, 1),
                (40, 250, 75, 262, "Other", 1, 0, 0),
                (77, 250, 110, 262, "income,", 1, 0, 1),
                (112, 250, 130, 262, "net", 1, 0, 2),
                (200, 250, 245, 262, "200", 1, 0, 3),
                (300, 250, 345, 262, "100", 1, 0, 4),
            ]

    class _FakeDoc:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def load_page(self, _idx: int):
            return _FakePage()

    monkeypatch.setattr(rect_finder, "find_rects_for_text", fake_find_rects_for_text)
    monkeypatch.setattr(fitz, "open", lambda _path: _FakeDoc())

    repo = _TestRepo(Path("/tmp/fake.pdf"))
    citation = _make_citation(
        cited_text=(
            "For the Quarter Ended June 29, 2024 June 30, 2025\n"
            "Other income, net 200 100"
        ),
        display_text="Other income, net",
        searchable_text="29.",
    )
    linked_message = Message(
        id="message-7",
        conversation_id="conversation-7",
        role="assistant",
        content=(
            "For the quarter ended June 29, 2024, the value was 200 thousand; for "
            "the quarter ended June 30, 2025, the value was $100 thousand. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id="message-7",
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1
    selected = api_citation["rects"][0]
    assert selected["x1"] == target_rect["x1"]
    assert selected["y1"] == pytest.approx(800.0 - target_rect["y2"])
    assert selected["y2"] == pytest.approx(800.0 - target_rect["y1"])


@pytest.mark.unit
def test_mueller_prefers_primary_answer_value_over_trailing_comparison_values():
    repo_root = Path(__file__).resolve().parents[4]
    pdf_path = repo_root / "ExampleDocs" / "Mueller Industries Earnings Release.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Missing sample PDF: {pdf_path}")

    repo = _TestRepo(pdf_path)
    citation = _make_citation(
        id="mueller-primary-vs-trailing-comparison",
        document_id="mueller-doc-2",
        page=2,
        start_page_number=2,
        end_page_number=3,
        text="Mueller income statement table",
        cited_text=(
            "MUELLER INDUSTRIES, INC.\n"
            "CONDENSED CONSOLIDATED STATEMENTS OF INCOME\n"
            "(Unaudited)\n"
            "For the Quarter Ended For the Six Months Ended\n"
            "(In thousands, except per share data)\n"
            "June 29, 2024 July 1, 2023 June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984 1,847,399 1,868,176\n"
            "Other (expense) income, net (1,356) 1,841 (726) 2,167\n"
            "Income before income taxes 222,926 240,958 424,476 478,392"
        ),
        display_text="(In thousands, except per share data): 29,",
        searchable_text="29",
        highlight_id="mueller-primary-vs-trailing-comparison",
    )
    linked_message = Message(
        id="message-primary-vs-trailing",
        conversation_id="conversation-primary-vs-trailing",
        role="assistant",
        content=(
            "# Financial Analysis of Mueller Industries Q2 2024 Earnings\n\n"
            "Based on the Mueller Industries' second quarter 2024 earnings report, "
            "I'll provide an analysis of the specific financial figure requested.\n\n"
            "For the quarter ended July 1, 2023, Other (expense) income, net was "
            "$1,841 thousand.\n\n"
            "This figure appears in the Condensed Consolidated Statements of Income "
            "for Mueller Industries, specifically in the income statement section that "
            "details the components contributing to the company's Income before income "
            "taxes.\n\n"
            "To provide context, this figure represents miscellaneous income or "
            "expenses that don't fit into the company's other more specific income "
            "statement categories. It's worth noting that this figure changed "
            "significantly in the most recent quarter (June 29, 2024), when it became "
            "an expense of $(1,356) thousand rather than income.\n\n"
            "The Other (expense) income, net line item is just one component of "
            "Mueller Industries' non-operating results, which also include interest "
            "expense, interest income, and realized/unrealized gains on short-term "
            "investments.\n\n"
            "## Concluding Insights\n\n"
            "The shift from Other income of $1,841 thousand in Q2 2023 to Other "
            "expense of $(1,356) thousand in Q2 2024 represents a negative swing of "
            "$3,197 thousand. While the company doesn't provide specific details about "
            "what comprises this line item, such changes in miscellaneous "
            "income/expense can result from various factors including foreign exchange "
            "impacts, disposal of assets, or other non-recurring items. This change "
            "contributed to the overall decrease in Income before income taxes from "
            "$240,958 thousand in Q2 2023 to $222,926 thousand in Q2 2024. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id=linked_message.id,
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1

    rect = api_citation["rects"][0]
    text = _extract_rect_text(pdf_path, rect)
    assert "1,841" in text
    assert "240,958" not in text


@pytest.mark.unit
def test_mueller_prefers_2024_column_when_answer_targets_june_2024():
    repo_root = Path(__file__).resolve().parents[4]
    pdf_path = repo_root / "ExampleDocs" / "Mueller Industries Earnings Release.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Missing sample PDF: {pdf_path}")

    repo = _TestRepo(pdf_path)
    citation = _make_citation(
        id="mueller-2024-column-focus",
        document_id="mueller-doc-2024",
        page=2,
        start_page_number=2,
        end_page_number=3,
        text="Mueller income statement table",
        cited_text=(
            "MUELLER INDUSTRIES, INC.\n"
            "CONDENSED CONSOLIDATED STATEMENTS OF INCOME\n"
            "(Unaudited)\n"
            "For the Quarter Ended For the Six Months Ended\n"
            "(In thousands, except per share data)\n"
            "June 29, 2024 July 1, 2023 June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984 1,847,399 1,868,176\n"
            "Other (expense) income, net (1,356) 1,841 (726) 2,167\n"
            "Income before income taxes 222,926 240,958 424,476 478,392"
        ),
        display_text="(In thousands, except per share data): 29,",
        searchable_text="29",
        highlight_id="mueller-2024-column-focus",
    )
    linked_message = Message(
        id="message-2024-column-focus",
        conversation_id="conversation-2024-column-focus",
        role="assistant",
        content=(
            "For the quarter ended June 29, 2024, Other (expense) income, net was "
            "$(1,356) thousand. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id=linked_message.id,
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1

    rect = api_citation["rects"][0]
    text = _extract_rect_text(pdf_path, rect)
    assert "1,356" in text
    assert "1,841" not in text


@pytest.mark.unit
def test_mueller_uses_nearest_column_cue_not_heading_year_for_primary_answer():
    repo_root = Path(__file__).resolve().parents[4]
    pdf_path = repo_root / "ExampleDocs" / "Mueller Industries Earnings Release.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Missing sample PDF: {pdf_path}")

    repo = _TestRepo(pdf_path)
    citation = _make_citation(
        id="mueller-heading-year-regression",
        document_id="mueller-doc-heading-year",
        page=2,
        start_page_number=2,
        end_page_number=3,
        text="Mueller income statement table",
        cited_text=(
            "MUELLER INDUSTRIES, INC.\n"
            "CONDENSED CONSOLIDATED STATEMENTS OF INCOME\n"
            "(Unaudited)\n"
            "For the Quarter Ended For the Six Months Ended\n"
            "(In thousands, except per share data)\n"
            "June 29, 2024 July 1, 2023 June 29, 2024 July 1, 2023\n"
            "Net sales 997,745 896,984 1,847,399 1,868,176\n"
            "Other (expense) income, net (1,356) 1,841 (726) 2,167\n"
            "Income before income taxes 222,926 240,958 424,476 478,392"
        ),
        display_text="(In thousands, except per share data): 29,",
        searchable_text="29",
        highlight_id="mueller-heading-year-regression",
    )
    linked_message = Message(
        id="message-heading-year-regression",
        conversation_id="conversation-heading-year-regression",
        role="assistant",
        content=(
            "# Analysis of Mueller Industries' Q2 2024 Financial Performance\n\n"
            "Based on the provided financial statement for Mueller Industries, Inc., "
            "I'll analyze the specific figure you're requesting along with relevant context.\n\n"
            "For the quarter ended July 1, 2023, Mueller Industries reported Other "
            "(expense) income, net of $1,841 thousand. This figure appears in the "
            "Condensed Consolidated Statements of Income in the financial report.\n\n"
            "It's worth noting that this figure has changed in the most recent quarter. "
            "For the quarter ended June 29, 2024, the company reported Other (expense) "
            "income, net of ($1,356) thousand, indicating a shift from income to expense. [1]"
        ),
    )
    citation.messages = [
        MessageCitation(
            message_id=linked_message.id,
            citation_id=str(citation.id),
            message=linked_message,
            citation=citation,
        )
    ]

    api_citation = repo.citation_to_api_schema(citation)
    assert len(api_citation["rects"]) == 1

    rect = api_citation["rects"][0]
    text = _extract_rect_text(pdf_path, rect)
    compact = text.replace(" ", "").replace(",", "")
    assert "1841" in compact
    assert "1356" not in compact
