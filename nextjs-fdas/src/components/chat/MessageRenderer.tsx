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
  
  // Handle the case where the same text appears multiple times
  // This can happen when analysis results contain duplicate text
  const detectDuplicateText = (content: string): string => {
    // Split content into sentences or meaningful chunks
    const lines = content.split('\n');
    
    // Check for exact duplicates of entire content
    if (content.includes(content.trim() + '\n' + content.trim())) {
      return content.trim();
    }
    
    // Check for duplicated first sentence/line (common case)
    if (lines.length > 1) {
      const firstLine = lines[0].trim();
      const restOfContent = lines.slice(1).join('\n');
      
      if (restOfContent.includes(firstLine) && firstLine.length > 10) {
        // The first line is duplicated somewhere in the rest of the content
        // Only return the content starting from the second instance
        const startOfDuplicate = restOfContent.indexOf(firstLine);
        return restOfContent.substring(startOfDuplicate);
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
