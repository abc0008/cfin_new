"""
Citation API routes for direct citation access.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.document_repository import DocumentRepository
from utils.database import get_db

router = APIRouter(prefix="/api/citations", tags=["citations"])


async def get_document_repository(db: AsyncSession = Depends(get_db)):
    """Dependency to get document repository instance."""
    return DocumentRepository(db)


@router.get("/{citation_id}")
async def get_citation_by_id(
    citation_id: str,
    document_repository: DocumentRepository = Depends(get_document_repository)
) -> Dict[str, Any]:
    """
    Get a citation by its ID directly.
    
    This endpoint allows frontend to fetch citation details without knowing
    the document ID, useful for citation links in chat messages.
    
    Args:
        citation_id: The unique citation ID
        
    Returns:
        Citation details in API format
        
    Raises:
        404 if citation not found
    """
    citation = await document_repository.get_citation(citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    
    return document_repository.citation_to_api_schema(citation)