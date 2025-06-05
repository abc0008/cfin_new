from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.document import router, get_document_service, get_analysis_repository



def create_client(doc_service_mock, analysis_repo_mock):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_document_service] = lambda: doc_service_mock
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo_mock
    return TestClient(app)


def test_delete_document_success():
    doc_service = MagicMock()
    doc_service.document_repository = MagicMock()
    doc_service.document_repository.get_document = AsyncMock(return_value=object())
    doc_service.delete_document = AsyncMock(return_value=True)
    analysis_repo = MagicMock()

    client = create_client(doc_service, analysis_repo)
    response = client.delete("/api/documents/doc-1")
    assert response.status_code == 200
    doc_service.delete_document.assert_awaited_with("doc-1", analysis_repo)


def test_delete_document_conflict():
    doc_service = MagicMock()
    doc_service.document_repository = MagicMock()
    doc_service.document_repository.get_document = AsyncMock(return_value=object())
    doc_service.delete_document = AsyncMock(side_effect=ValueError("Document is referenced by an analysis"))
    analysis_repo = MagicMock()

    client = create_client(doc_service, analysis_repo)
    response = client.delete("/api/documents/doc-1")
    assert response.status_code == 409
    assert "referenced" in response.json()["detail"]

