'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, Copy, CheckCircle2, BarChart } from 'lucide-react';

// Types for the various interactive elements
export type SuggestionAction = {
  label: string;
  action: () => void;
  icon?: React.ReactNode;
  variant?: 'default' | 'primary' | 'outline' | 'secondary';
};

export type ExpandableContentProps = {
  summary: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
};

export type FeedbackProps = {
  messageId: string;
  onFeedback: (messageId: string, isPositive: boolean) => void;
};

export type AnalysisActionProps = {
  documentIds: string[];
  onRequestAnalysis: (documentIds: string[]) => void;
};

// Suggestion Chips component
export const SuggestionChips = ({ suggestions }: { suggestions: SuggestionAction[] }) => {
  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          onClick={suggestion.action}
          className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-avenir-pro transition-colors ${
            suggestion.variant === 'primary'
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : suggestion.variant === 'outline'
              ? 'border border-border text-foreground hover:bg-muted'
              : suggestion.variant === 'secondary'
              ? 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
              : 'bg-card border border-border text-foreground hover:bg-muted'
          }`}
        >
          {suggestion.icon && <span className="mr-1.5">{suggestion.icon}</span>}
          {suggestion.label}
        </button>
      ))}
    </div>
  );
};

// Expandable Content component
export const ExpandableContent = ({ summary, children, defaultExpanded = false }: ExpandableContentProps) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="mt-2 border border-border rounded-md overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 text-left bg-muted hover:bg-muted/80 flex justify-between items-center font-avenir-pro transition-colors"
      >
        <span className="font-avenir-pro-demi text-foreground">{summary}</span>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {isExpanded && (
        <div className="p-4 bg-card">
          <div className="font-avenir-pro text-foreground">
            {children}
          </div>
        </div>
      )}
    </div>
  );
};

// Message Feedback component
export const MessageFeedback = ({ messageId, onFeedback }: FeedbackProps) => {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);

  const handleFeedback = (isPositive: boolean) => {
    const feedbackType = isPositive ? 'positive' : 'negative';
    setFeedback(feedbackType);
    onFeedback(messageId, isPositive);
  };

  return (
    <div className="flex items-center space-x-2 mt-2">
      <span className="text-xs text-muted-foreground font-avenir-pro">Was this helpful?</span>
      <button
        onClick={() => handleFeedback(true)}
        className={`p-1 rounded-md transition-colors ${
          feedback === 'positive' ? 'bg-secondary/20 text-secondary' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
        }`}
        aria-label="Thumbs up"
      >
        <ThumbsUp className="h-4 w-4" />
      </button>
      <button
        onClick={() => handleFeedback(false)}
        className={`p-1 rounded-md transition-colors ${
          feedback === 'negative' ? 'bg-destructive/20 text-destructive' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
        }`}
        aria-label="Thumbs down"
      >
        <ThumbsDown className="h-4 w-4" />
      </button>
    </div>
  );
};

// Copy to Clipboard component
export const CopyToClipboard = ({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      aria-label="Copy to clipboard"
    >
      {copied ? (
        <CheckCircle2 className="h-4 w-4 text-secondary" />
      ) : (
        <Copy className="h-4 w-4" />
      )}
    </button>
  );
};

// Analysis Request button
export const AnalysisAction = ({ documentIds, onRequestAnalysis }: AnalysisActionProps) => {
  return (
    <button
      onClick={() => onRequestAnalysis(documentIds)}
      className="mt-3 inline-flex items-center px-3 py-1.5 rounded-md text-sm font-avenir-pro bg-accent/10 text-accent hover:bg-accent/20 border border-accent/20 transition-colors"
    >
      <BarChart className="h-4 w-4 mr-1.5" />
      Generate Financial Analysis
    </button>
  );
};

// Message Actions container
export const MessageActions = ({ 
  children,
  className = ""
}: { 
  children: React.ReactNode;
  className?: string;
}) => {
  return (
    <div className={`flex items-center justify-end space-x-2 mt-1 ${className}`}>
      {children}
    </div>
  );
};
