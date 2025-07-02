"""
Citation parsing and processing service for Anthropic API responses.
"""

import uuid
import json
from typing import Dict, List, Tuple, Optional, Any
from models.citation import (
    Citation, CitationPayload, CitationType, 
    CharLocationCitation, PageLocationCitation, ContentBlockLocationCitation
)


def parse_citations(
    content_blocks: List[Dict[str, Any]], 
    document_map: Dict[int, str]
) -> Tuple[str, List[CitationPayload]]:
    """
    Parse citations from Claude's response content blocks.
    
    Args:
        content_blocks: List of content blocks from Claude's response
        document_map: Mapping from document index to document ID
        
    Returns:
        Tuple of (rendered text with citation markers, list of citations)
    """
    rendered_parts = []
    citations = []
    citation_counter = 1
    
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "")
            
            # Check if this block has citations
            block_citations = block.get("citations", [])
            
            # Add citation markers at the end of the text for each citation
            for citation_data in block_citations:
                # Generate unique IDs
                citation_id = str(uuid.uuid4())
                highlight_id = citation_id  # Use same ID for highlight
                
                # Get document ID from map
                doc_index = citation_data.get("document_index", 0)
                doc_id = document_map.get(doc_index, "")
                
                # Create citation object
                citation = create_citation_from_anthropic(
                    citation_data, 
                    citation_id, 
                    highlight_id,
                    doc_id
                )
                citations.append(citation)
                
                # Add marker to text
                text += f"[{citation_counter}]"
                citation_counter += 1
            
            rendered_parts.append(text)
    
    # Join all text parts
    rendered_text = "".join(rendered_parts)
    
    return rendered_text, citations


def create_citation_from_anthropic(
    data: Dict[str, Any], 
    citation_id: str, 
    highlight_id: str,
    doc_id: str
) -> CitationPayload:
    """
    Convert Anthropic citation format to our CitationPayload model.
    
    Args:
        data: Citation data from Anthropic API
        citation_id: Unique ID for this citation
        highlight_id: ID for highlighting in PDF viewer
        doc_id: Database document ID
        
    Returns:
        CitationPayload object
    """
    # Base fields common to all citation types
    base_fields = {
        "id": citation_id,
        "highlight_id": highlight_id,
        "document_id": doc_id,
        "type": CitationType(data["type"]),
        "cited_text": data.get("cited_text", ""),
        "document_title": data.get("document_title", ""),
        "rects": []  # Will be populated later with coordinate mapping
    }
    
    # Add type-specific fields
    citation_type = data["type"]
    
    if citation_type == "page_location":
        base_fields.update({
            "start_page_number": data.get("start_page_number"),
            "end_page_number": data.get("end_page_number"),
            "page": data.get("start_page_number")  # Legacy compatibility
        })
    elif citation_type == "char_location":
        base_fields.update({
            "start_char_index": data.get("start_char_index"),
            "end_char_index": data.get("end_char_index")
        })
    elif citation_type == "content_block_location":
        base_fields.update({
            "start_block_index": data.get("start_block_index"),
            "end_block_index": data.get("end_block_index")
        })
    
    return CitationPayload(**base_fields)


def deduplicate_citations(
    citations: List[CitationPayload], 
    existing_citations: Optional[List[CitationPayload]] = None
) -> List[CitationPayload]:
    """
    Deduplicate citations based on signature (document, location, text).
    
    Args:
        citations: New citations to process
        existing_citations: Optional list of existing citations to check against
        
    Returns:
        List of unique citations
    """
    seen_signatures = set()
    unique_citations = []
    
    # Add existing citation signatures if provided
    if existing_citations:
        for citation in existing_citations:
            signature = get_citation_signature(citation)
            seen_signatures.add(signature)
    
    # Process new citations
    for citation in citations:
        signature = get_citation_signature(citation)
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_citations.append(citation)
    
    return unique_citations


def get_citation_signature(citation: CitationPayload) -> str:
    """
    Generate a unique signature for citation deduplication.
    
    Args:
        citation: Citation to generate signature for
        
    Returns:
        String signature
    """
    parts = [
        citation.document_id,
        citation.type.value,
        citation.cited_text[:100]  # First 100 chars to handle long citations
    ]
    
    # Add type-specific location data
    if citation.type == CitationType.PAGE_LOCATION:
        parts.extend([
            str(citation.start_page_number or 0),
            str(citation.end_page_number or 0)
        ])
    elif citation.type == CitationType.CHAR_LOCATION:
        parts.extend([
            str(citation.start_char_index or 0),
            str(citation.end_char_index or 0)
        ])
    elif citation.type == CitationType.CONTENT_BLOCK_LOCATION:
        parts.extend([
            str(citation.start_block_index or 0),
            str(citation.end_block_index or 0)
        ])
    
    return "|".join(parts)


def handle_streaming_citation(
    citation_delta: Dict[str, Any],
    current_block_index: int,
    pending_citations: Dict[int, List[CitationPayload]],
    document_map: Dict[int, str]
) -> None:
    """
    Handle a citation delta from streaming response.
    
    Args:
        citation_delta: Citation data from streaming delta
        current_block_index: Index of current text block
        pending_citations: Map of block index to pending citations
        document_map: Mapping from document index to document ID
    """
    # Get or create citation list for this block
    block_citations = pending_citations.get(current_block_index, [])
    
    # Create citation from delta
    citation_id = str(uuid.uuid4())
    highlight_id = citation_id
    doc_index = citation_delta.get("document_index", 0)
    doc_id = document_map.get(doc_index, "")
    
    new_citation = create_citation_from_anthropic(
        citation_delta,
        citation_id,
        highlight_id,
        doc_id
    )
    
    # Check for duplicates
    signature = get_citation_signature(new_citation)
    if not any(get_citation_signature(c) == signature for c in block_citations):
        block_citations.append(new_citation)
        pending_citations[current_block_index] = block_citations