'use client';

import { useEffect, useState } from 'react';
import { File, Loader2, AlertCircle, Eye, Trash2, ChevronRight, BarChart } from 'lucide-react';
import { DocumentMetadata } from '@/types';
import { documentsApi } from '@/lib/api/documents';

interface DocumentListProps {
  refreshTrigger?: number;
  onSelectDocument?: (documentId: string) => void;
  onDelete?: (documentId: string) => void;
  onAnalyze?: (documentId: string) => void;
}

export function DocumentList({ 
  refreshTrigger = 0, 
  onSelectDocument,
  onDelete,
  onAnalyze
}: DocumentListProps) {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  
  const fetchDocuments = async (currentPage: number = page) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await documentsApi.listDocuments(currentPage, pageSize);
      
      // Handle response - it might be an array directly or an object with documents property
      let documentsList: DocumentMetadata[] = [];
      let documentsTotal: number = 0;
      
      if (Array.isArray(response)) {
        // Response is directly an array of documents
        documentsList = response as DocumentMetadata[];
        documentsTotal = response.length;
      } else if (response && typeof response === 'object' && 'documents' in response) {
        // Response is an object with documents and total properties
        documentsList = Array.isArray((response as any).documents) ? (response as any).documents : [];
        documentsTotal = typeof (response as any).total === 'number' ? (response as any).total : documentsList.length;
      } else {
        console.warn('Unexpected response format from listDocuments:', response);
        documentsList = [];
        documentsTotal = 0;
      }
      
      // If loading the first page, replace the list
      if (currentPage === 1) {
        setDocuments(documentsList);
      } else {
        // Otherwise append to the existing list
        setDocuments(prev => [...(prev || []), ...documentsList]);
      }
      
      setTotal(documentsTotal);
      setHasMore(documentsTotal > currentPage * pageSize);
      setIsLoading(false);
      
      // Update the document count in the dashboard metric card
      const documentCountElement = document.getElementById('document-count');
      if (documentCountElement) {
        documentCountElement.textContent = documentsTotal.toString();
      }
      
    } catch (err) {
      console.error('Error fetching documents:', err);
      setError(err instanceof Error ? err.message : 'Failed to load documents');
      setDocuments([]); // Ensure documents is always an array
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    // Reset to page 1 and fetch whenever the refresh trigger changes
    setPage(1);
    fetchDocuments(1);
  }, [refreshTrigger]);
  
  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchDocuments(nextPage);
  };
  
  const handleSelectDocument = (documentId: string) => {
    if (onSelectDocument) {
      onSelectDocument(documentId);
    }
  };
  
  const handleDeleteDocument = async (documentId: string) => {
    if (confirm('Are you sure you want to delete this document?')) {
      try {
        await documentsApi.deleteDocument(documentId);
        // Remove from the local state
        setDocuments(prev => (prev || []).filter(doc => doc.id !== documentId));
        setTotal(prev => Math.max(0, prev - 1));
        
        // Update the document count in the dashboard
        const documentCountElement = document.getElementById('document-count');
        if (documentCountElement) {
          documentCountElement.textContent = Math.max(0, total - 1).toString();
        }
        
        // Call the parent callback if provided
        if (onDelete) {
          onDelete(documentId);
        }
      } catch (error) {
        console.error('Error deleting document:', error);
        setError('Failed to delete document');
      }
    }
  };
  
  const handleAnalyzeDocument = (documentId: string) => {
    if (onAnalyze) {
      onAnalyze(documentId);
    }
  };
  
  if (error) {
    return (
      <div className="p-4 border border-destructive/20 rounded-lg flex items-center bg-destructive/10 text-destructive mb-4">
        <AlertCircle className="h-5 w-5 flex-shrink-0" />
        <div className="font-avenir-pro text-sm ml-3 flex-1">{error}</div>
        <button 
          onClick={() => fetchDocuments(1)} 
          className="btn-outline ml-4 py-2 px-3 text-sm"
        >
          Try Again
        </button>
      </div>
    );
  }
  
  const safeDocuments = documents || [];
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="font-avenir-pro-demi text-lg text-foreground">Your Documents</h3>
        <div className="font-avenir-pro text-sm text-muted-foreground">
          {total} document{total !== 1 ? 's' : ''}
        </div>
      </div>
      
      {safeDocuments.length === 0 && !isLoading ? (
        <div className="text-center py-12 border border-border rounded-lg bg-muted/30">
          <File className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <h4 className="font-avenir-pro-demi text-lg text-foreground mb-2">No documents yet</h4>
          <p className="font-avenir-pro-light text-muted-foreground">
            Upload your first PDF to get started with financial analysis.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {safeDocuments.map(doc => (
            <div 
              key={doc.id} 
              className="flex items-center justify-between p-6 border border-border rounded-lg bg-card hover:border-primary/20 transition-all duration-200 hover:shadow-sm"
            >
              <div 
                className="flex items-center flex-1 min-w-0 cursor-pointer" 
                onClick={() => handleSelectDocument(doc.id)}
              >
                <div className="p-3 bg-primary/10 rounded-lg mr-4">
                  <File className="h-6 w-6 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-avenir-pro-demi text-foreground truncate text-base">
                    {doc.filename}
                  </div>
                  <div className="font-avenir-pro-light text-sm text-muted-foreground mt-1">
                    Uploaded {new Date(doc.uploadTimestamp).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                  {doc.citationLinks && doc.citationLinks.length > 0 && (
                    <div className="font-avenir-pro text-xs text-secondary mt-2 flex items-center">
                      <div className="h-1.5 w-1.5 bg-secondary rounded-full mr-2"></div>
                      {doc.citationLinks.length} citation{doc.citationLinks.length !== 1 ? 's' : ''} available
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center space-x-2 ml-6">
                <button 
                  className="p-3 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  onClick={() => handleSelectDocument(doc.id)}
                  title="View document"
                >
                  <Eye className="h-5 w-5" />
                </button>
                {onAnalyze && (
                  <button
                    className="p-3 rounded-lg text-muted-foreground hover:bg-secondary/10 hover:text-secondary transition-colors"
                    onClick={() => handleAnalyzeDocument(doc.id)}
                    title="Analyze document"
                  >
                    <BarChart className="h-5 w-5" />
                  </button>
                )}
                <button 
                  className="p-3 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                  onClick={() => handleDeleteDocument(doc.id)}
                  title="Delete document"
                >
                  <Trash2 className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center p-6 border border-border rounded-lg bg-card">
                  <div className="h-12 w-12 rounded-lg bg-muted animate-pulse mr-4"></div>
                  <div className="flex-1">
                    <div className="h-5 w-2/3 bg-muted animate-pulse mb-3"></div>
                    <div className="h-4 w-1/3 bg-muted animate-pulse"></div>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {hasMore && !isLoading && (
            <button 
              className="btn-outline w-full justify-center"
              onClick={handleLoadMore} 
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  Load More
                  <ChevronRight className="h-5 w-5 ml-2" />
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
} 