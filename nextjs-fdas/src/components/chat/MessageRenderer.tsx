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
  // Function to render content with citation markers
  const renderContentWithCitations = (
    content: string,
    citations: Citation[],
    onCitationClick?: (citation: Citation) => void
  ): React.ReactNode => {
    if (!citations || citations.length === 0) {
      return <MarkdownRenderer content={content} />;
    }

    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Find and replace citation markers [1], [2], etc.
    const citationPattern = /\[(\d+)\]/g;
    let match;

    while ((match = citationPattern.exec(content)) !== null) {
      const citationIndex = parseInt(match[1], 10) - 1;
      
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(
          <MarkdownRenderer 
            key={`text-${lastIndex}`}
            content={content.substring(lastIndex, match.index)} 
          />
        );
      }

      // Add clickable citation
      if (citations[citationIndex]) {
        const citation = citations[citationIndex];
        parts.push(
          <button
            key={`cite-${citation.id}`}
            className="citation-link inline-flex items-center px-1 py-0.5 mx-0.5 rounded bg-yellow-100 text-yellow-800 hover:bg-yellow-200 border border-yellow-200 cursor-pointer text-xs align-top"
            onClick={() => onCitationClick?.(citation)}
            aria-label={`Citation ${citationIndex + 1}: ${citation.citedText.substring(0, 50)}...`}
          >
            <sup className="font-medium">{citationIndex + 1}</sup>
          </button>
        );
      } else {
        // Fallback if citation not found
        parts.push(
          <sup key={`cite-fallback-${match.index}`} className="text-gray-500">
            [{match[1]}]
          </sup>
        );
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push(
        <MarkdownRenderer 
          key={`text-${lastIndex}`}
          content={content.substring(lastIndex)} 
        />
      );
    }

    return <>{parts}</>;
  };

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

  // For assistant messages with citations, render with citation markers
  if (message.citations && message.citations.length > 0) {
    return (
      <div className="message-content">
        {renderContentWithCitations(processedContent, message.citations, onCitationClick)}
      </div>
    );
  }

  // For assistant messages without citations, use whitespace-pre-wrap to preserve formatting
  return (
    <div className="message-content whitespace-pre-wrap">
      {processedContent}
    </div>
  );
}

// Export the memoized version of the component
export const MessageRenderer = React.memo(MessageRendererBase, areEqual);
