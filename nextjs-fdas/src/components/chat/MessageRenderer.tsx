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
    
    // Check if content has both formatted and unformatted versions
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
    
    return content;
  };
  
  // Apply duplicate detection and removal
  processedContent = detectDuplicateText(processedContent);

  return (
    <MarkdownRenderer 
      content={processedContent} 
      citations={message.citations}
      onCitationClick={onCitationClick}
    />
  );
}

// Export the memoized version of the component
export const MessageRenderer = React.memo(MessageRendererBase, areEqual);
