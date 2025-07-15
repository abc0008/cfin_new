'use client';

import React from 'react';
import { Citation } from '@/types';

interface TextWithCitationsProps {
  text: string;
  citations: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

export function TextWithCitations({ 
  text, 
  citations, 
  onCitationClick 
}: TextWithCitationsProps) {
  // Parse text and replace citation markers with clickable links
  const renderTextWithCitations = () => {
    if (!text) return null;
    
    // Find all citation markers in the text
    const citationPattern = /\[(\d+)\]/g;
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let match;
    
    while ((match = citationPattern.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      
      // Get citation index (1-based from the marker)
      const citationIndex = parseInt(match[1]) - 1;
      const citation = citations[citationIndex];
      
      if (citation) {
        // Add clickable citation
        parts.push(
          <button
            key={`citation-${match.index}`}
            onClick={() => onCitationClick?.(citation)}
            className="inline-flex items-center px-1 py-0.5 mx-0.5 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200 transition-colors cursor-pointer"
            title={`Page ${
              // Prefer explicit startPageNumber if present, otherwise fallback
              citation.startPageNumber ??
              (citation.rects && citation.rects.length > 0 ? citation.rects[0].pageNumber : undefined) ??
              citation.endPageNumber ??
              'N/A'
            }`}
          >
            [{match[1]}]
          </button>
        );
      } else {
        // No matching citation, just show the marker as plain text
        parts.push(match[0]);
      }
      
      lastIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }
    
    return parts;
  };
  
  return <>{renderTextWithCitations()}</>;
}