'use client';

import React, { useMemo } from 'react';
import { Message, Citation } from '@/types';
import { ExternalLink } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface MessageRendererProps {
  message: Message;
  onCitationClick?: (citation: Citation) => void;
}

// Custom equality function to prevent unnecessary re-renders
function areEqual(prevProps: MessageRendererProps, nextProps: MessageRendererProps): boolean {
  const prevMsg = prevProps.message;
  const nextMsg = nextProps.message;
  
  // If IDs are the same, they're the same message
  if (prevMsg.id === nextMsg.id) return true;
  
  // If content is identical, don't re-render
  if (prevMsg.content && nextMsg.content && 
      prevMsg.content.trim() === nextMsg.content.trim() &&
      prevMsg.role === nextMsg.role) {
    return true;
  }
  
  // Otherwise, re-render
  return false;
}

function MessageRendererBase({ message, onCitationClick }: MessageRendererProps) {
  // Return early if no content
  if (!message.content) {
    return null;
  }
  
  // For system messages, use simple line breaks without markdown
  if (message.role === 'system') {
    return (
      <div className="message-content">
        {message.content.split('\n').map((line, i) => (
          <div key={i} className={i > 0 ? 'mt-2' : ''}>
            {line}
          </div>
        ))}
      </div>
    );
  }

  // For user messages, use simple text with line breaks
  if (message.role === 'user') {
    return (
      <div className="message-content">
        {message.content.split('\n').map((line, i) => (
          <div key={i} className={i > 0 ? 'mt-2' : ''}>
            {line}
          </div>
        ))}
      </div>
    );
  }

  // For assistant messages:
  // Process content to handle potential duplications from the backend
  // Detect and remove duplicate content in assistant messages
  let processedContent = message.content;
  
  // Handle the case where formatted content is followed by unformatted duplicate
  // This happens when streaming content is duplicated without formatting
  const detectDuplicateText = (content: string): string => {
    // First, check if the content ends with an unformatted version of itself
    // The pattern is: formatted content with newlines and numbering, followed by
    // the same content as one long string without proper formatting
    
    // Extract the text content without formatting
    const getPlainText = (text: string): string => {
      // Remove markdown formatting, numbers, bullets, etc.
      return text
        .replace(/^\d+\.\s+/gm, '') // Remove numbered lists
        .replace(/^[-*]\s+/gm, '') // Remove bullet points
        .replace(/^#+\s+/gm, '') // Remove headers
        .replace(/\*\*/g, '') // Remove bold
        .replace(/\*/g, '') // Remove italic
        .replace(/\n+/g, ' ') // Replace newlines with spaces
        .replace(/\s+/g, ' ') // Normalize spaces
        .trim();
    };
    
    // First check: Look for exact duplicates where content appears twice
    const halfLength = Math.floor(content.length / 2);
    if (content.length > 100) {
      const firstHalf = content.substring(0, halfLength);
      const secondHalf = content.substring(halfLength);
      
      // Check if the content is literally duplicated
      if (firstHalf.trim() === secondHalf.trim()) {
        return firstHalf.trim();
      }
    }
    
    // Second check: Check if content has both formatted and unformatted versions
    const lines = content.split('\n');
    if (lines.length > 0) {
      // Get the last line which might be the unformatted duplicate
      const lastLine = lines[lines.length - 1].trim();
      
      // If the last line is very long and contains no formatting
      if (lastLine.length > 200 && !lastLine.includes('\n')) {
        // Get all content except the last line
        const formattedContent = lines.slice(0, -1).join('\n').trim();
        
        // Compare plain text versions
        const formattedPlain = getPlainText(formattedContent);
        const lastLinePlain = getPlainText(lastLine);
        
        // If they're essentially the same content, keep only the formatted version
        if (formattedPlain.length > 100 && 
            (lastLinePlain.includes(formattedPlain.substring(0, 100)) || 
             formattedPlain.includes(lastLinePlain.substring(0, 100)))) {
          return formattedContent;
        }
      }
    }
    
    // Third check: Look for content that starts repeating mid-way
    // This handles cases where backend duplicates from a certain point
    if (content.length > 200) {
      // Look for repeated patterns in the content
      const plainContent = getPlainText(content);
      const searchLength = Math.min(100, Math.floor(plainContent.length / 4));
      const searchPattern = plainContent.substring(0, searchLength);
      
      // Find if this pattern appears again later in the content
      const secondOccurrence = plainContent.indexOf(searchPattern, searchLength);
      if (secondOccurrence > searchLength) {
        // Found a duplicate pattern, extract the non-duplicated part
        const originalContent = content.substring(0, secondOccurrence);
        return originalContent.trim();
      }
    }
    
    return content;
  };
  
  // Apply duplicate detection and removal
  processedContent = detectDuplicateText(processedContent);

  // Helper function to parse content and embed clickable citations
  const renderContentWithCitations = (
    contentToRender: string,
    citations: Citation[] | undefined,
    handleCitationClick: ((citation: Citation) => void) | undefined
  ) => {
    if (!citations || citations.length === 0 || !handleCitationClick || !contentToRender) {
      // If no citations or no handler, or no content, render plain content (potentially markdown)
      // Using MarkdownRenderer for assistant messages if they might contain markdown.
      // If they are plain text, then simple div per line or direct text is fine.
      return <MarkdownRenderer content={contentToRender} />;
    }

    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    // Regex to find placeholders like [1], [2], etc.
    // Using string.replace with a callback function to build the parts array
    contentToRender.replace(/\[(\d+)\]/g, (match, p1, offset) => {
      const citationNumber = parseInt(p1, 10);
      const citationIndex = citationNumber - 1; // Citations are 1-indexed in text

      // Add text part before the current match
      if (offset > lastIndex) {
        parts.push(
          <MarkdownRenderer
            key={`text-${lastIndex}`}
            content={contentToRender.substring(lastIndex, offset)}
          />
        );
      }

      if (citations[citationIndex]) {
        const citation = citations[citationIndex];
        parts.push(
          <span
            key={`citation-${citation.id || citationIndex}`}
            className="text-primary hover:text-primary/80 underline cursor-pointer font-semibold mx-0.5 px-0.5 rounded-sm focus:outline-none focus:ring-2 focus:ring-primary"
            onClick={(e) => {
              e.stopPropagation(); // Prevent any parent onClick if MessageRenderer is part of a larger clickable area
              handleCitationClick(citation);
            }}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.stopPropagation();
                handleCitationClick(citation);
              }
            }}
            aria-label={`Citation ${citationNumber}, Text: ${citation.text.substring(0, 30)}...`}
          >
            {`[${citationNumber}]`}
          </span>
        );
      } else {
        // If citation not found (e.g., malformed content), render the marker as text
        parts.push(match);
      }
      lastIndex = offset + match.length;
      return match; // Required by .replace(), not used for output array
    });

    // Add any remaining text after the last citation marker
    if (lastIndex < contentToRender.length) {
      parts.push(
        <MarkdownRenderer
          key={`text-${lastIndex}-end`}
          content={contentToRender.substring(lastIndex)}
        />
      );
    }

    // If no markers were found, parts will be empty, return original content via MarkdownRenderer
    if (parts.length === 0 && contentToRender) {
        return <MarkdownRenderer content={contentToRender} />;
    }

    return <>{parts}</>;
  };

  // For assistant messages, use whitespace-pre-wrap to preserve formatting
  return (
    <div className="message-content whitespace-pre-wrap">
      {renderContentWithCitations(processedContent, message.citations, onCitationClick)}
    </div>
  );
}

// Export the memoized version of the component
export const MessageRenderer = React.memo(MessageRendererBase, areEqual);
