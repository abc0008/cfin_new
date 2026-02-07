'use client';

import React from 'react';
import { Loader2, FileSearch, CheckCircle2, AlertCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

export interface CitationProgressProps {
  status: 'idle' | 'searching' | 'processing' | 'complete' | 'error';
  progress?: number;
  message?: string;
  totalPages?: number;
  currentPage?: number;
  foundCount?: number;
}

export function CitationProgress({
  status,
  progress = 0,
  message,
  totalPages,
  currentPage,
  foundCount = 0
}: CitationProgressProps) {
  const getIcon = () => {
    switch (status) {
      case 'searching':
        return <FileSearch className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-primary animate-spin" />;
      case 'complete':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'searching':
        if (totalPages && currentPage) {
          return `Searching page ${currentPage} of ${totalPages}...`;
        }
        return 'Searching for citations...';
      case 'processing':
        return 'Processing citations...';
      case 'complete':
        return `Found ${foundCount} citation${foundCount !== 1 ? 's' : ''}`;
      case 'error':
        return message || 'Error loading citations';
      default:
        return '';
    }
  };

  if (status === 'idle') {
    return null;
  }

  return (
    <div className="w-full space-y-2 p-4 bg-background/50 backdrop-blur rounded-lg border">
      <div className="flex items-center gap-2">
        {getIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
      </div>
      
      {status === 'searching' && progress > 0 && (
        <Progress value={progress} className="h-2" />
      )}
      
      {message && status !== 'error' && (
        <p className="text-xs text-muted-foreground">{message}</p>
      )}
    </div>
  );
}

export function CitationSearchProgress({
  isSearching,
  searchProgress,
  totalDocuments,
  currentDocument,
  foundCitations
}: {
  isSearching: boolean;
  searchProgress: number;
  totalDocuments?: number;
  currentDocument?: number;
  foundCitations: number;
}) {
  if (!isSearching && foundCitations === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <CitationProgress
        status={isSearching ? 'searching' : 'complete'}
        progress={searchProgress}
        totalPages={totalDocuments}
        currentPage={currentDocument}
        foundCount={foundCitations}
        message={
          isSearching && totalDocuments && currentDocument
            ? `Document ${currentDocument} of ${totalDocuments}`
            : undefined
        }
      />
    </div>
  );
}