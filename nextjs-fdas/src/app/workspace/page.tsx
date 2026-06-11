'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText, BarChart2, Upload, FileUp, ChevronRight, FileSearch } from 'lucide-react'
import { StreamingChatInterface } from '../../components/chat/StreamingChatInterface'
import { UploadForm } from '../../components/document/UploadForm'
import dynamic from 'next/dynamic'
import { ProcessedDocument, AnalysisResult, Message, Citation } from '@/types'
import { conversationApi } from '@/lib/api/conversation'
import { conversationsApi } from '@/lib/api/conversations'
import { analysisApi } from '@/lib/api/analysis'
import { documentsApi } from '@/lib/api/documents'
import Canvas from '@/components/visualization/Canvas'
import { AnalysisControls } from '@/components/analysis/AnalysisControls'
import { AnalysisResultSchema } from '@/validation/schemas'
import { useCitation } from '@/context/CitationContext'
import { ConversationSidebar } from '@/components/workspace/ConversationSidebar'

// localStorage key used to resume the most recent session across visits.
const LAST_SESSION_STORAGE_KEY = 'cfin:lastSessionId'

// Import CitationEnabledPDFViewer component with dynamic import to avoid SSR issues
const PDFViewer = dynamic(
  () => import('../../components/document/CitationEnabledPDFViewer').then(mod => mod.CitationEnabledPDFViewer),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading PDF viewer...</div>
      </div>
    )
  }
)

export default function Workspace() {
  const { citations, addCitations } = useCitation();
  const [activeTab, setActiveTab] = useState<'document' | 'analysis'>('document')
  // Store messages as a normalized object with ID as key for better deduplication
  const [messagesMap, setMessagesMap] = useState<Record<string, Message>>({});
  // Derive the array form only when needed for rendering
  const messages = useMemo(() => {
    return Object.values(messagesMap).sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [messagesMap]);
  
  const [selectedDocument, setSelectedDocument] = useState<ProcessedDocument | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [showReflectionsDialog, setShowReflectionsDialog] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const processedAnalysisMessageIdsRef = useRef<Set<string>>(new Set());
  const analysisRequestInFlightRef = useRef<Set<string>>(new Set());
  const initSessionRunRef = useRef(0);
  const documentPanelRef = useRef<HTMLDivElement | null>(null);
  
  // Message ID generation with hash to ensure uniqueness
  const generateMessageId = useCallback((role: string, content: string) => {
    // Simple hash function to generate a consistent hash for the same content
    const hashContent = (str: string) => {
      let hash = 0;
      for (let i = 0; i <str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
      }
      return Math.abs(hash).toString(16);
    };
    
    const contentHash = hashContent(content);
    const timestamp = Date.now();
    return `msg-${role}-${contentHash}-${timestamp}`;
  }, []);

  // ── Session lifecycle (multi-session memory) ──────────────────────────────

  const persistLastSession = useCallback((conversationId: string | null) => {
    try {
      if (conversationId) {
        window.localStorage.setItem(LAST_SESSION_STORAGE_KEY, conversationId);
      } else {
        window.localStorage.removeItem(LAST_SESSION_STORAGE_KEY);
      }
    } catch {
      /* storage unavailable */
    }
  }, []);

  const syncWorkspaceUrl = useCallback((conversationId: string | null) => {
    try {
      const url = conversationId
        ? `/workspace?conversationId=${encodeURIComponent(conversationId)}`
        : '/workspace';
      window.history.replaceState({}, '', url);
    } catch {
      /* no-op */
    }
  }, []);

  const resetWorkspaceState = useCallback(() => {
    setMessagesMap({});
    setAnalysisResults([]);
    setAnalysisError(null);
    setHighlightId(null);
    processedAnalysisMessageIdsRef.current = new Set();
    analysisRequestInFlightRef.current = new Set();
  }, []);

  // Load an existing conversation (history + attached documents) into the workspace.
  const loadConversation = useCallback(
    async (conversationId: string, preferredDocumentId?: string | null) => {
      setIsLoading(true);
      try {
        const [history, conversationDocs] = await Promise.all([
          conversationsApi.getConversationHistory(conversationId, 100),
          conversationsApi.getConversationDocuments(conversationId),
        ]);

        let documentToShow: ProcessedDocument | null = null;
        const docIdToLoad =
          preferredDocumentId ||
          (conversationDocs.length > 0
            ? conversationDocs[conversationDocs.length - 1].id
            : null);
        if (docIdToLoad) {
          try {
            documentToShow = await documentsApi.getDocument(docIdToLoad);
          } catch (docErr) {
            console.warn('Could not load conversation document:', docIdToLoad, docErr);
          }
        }

        resetWorkspaceState();
        setSessionId(conversationId);
        setSelectedDocument(documentToShow);
        setMessagesMap(
          history.reduce<Record<string, Message>>((acc, message) => {
            acc[message.id] = message;
            return acc;
          }, {})
        );
        persistLastSession(conversationId);
        syncWorkspaceUrl(conversationId);

        console.log('Loaded workspace session:', {
          conversationId,
          documentId: documentToShow?.metadata?.id,
          messageCount: history.length,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [persistLastSession, resetWorkspaceState, syncWorkspaceUrl]
  );

  // Create a brand-new conversation; keeps the current document attached so an
  // analyst can spin up a fresh thread on the same filing in one click.
  const createNewConversation = useCallback(
    async (documentId?: string | null) => {
      setIsLoading(true);
      try {
        const [response, document] = await Promise.all([
          conversationApi.createConversation(
            'New Conversation',
            documentId ? [documentId] : []
          ),
          documentId ? documentsApi.getDocument(documentId) : Promise.resolve(null),
        ]);
        const sessionIdValue =
          (response as any).sessionId || (response as any).session_id;
        resetWorkspaceState();
        setSessionId(sessionIdValue);
        setSelectedDocument(document);
        persistLastSession(sessionIdValue);
        syncWorkspaceUrl(sessionIdValue);
        setHistoryRefreshKey((k) => k + 1);
        console.log('Created conversation session:', sessionIdValue);
        return sessionIdValue as string;
      } finally {
        setIsLoading(false);
      }
    },
    [persistLastSession, resetWorkspaceState, syncWorkspaceUrl]
  );

  // Initialize the workspace session on mount:
  // 1. A deep link (?conversationId=…) wins.
  // 2. Otherwise resume the most recent session from localStorage.
  // 3. Otherwise create a fresh conversation.
  useEffect(() => {
    const runId = ++initSessionRunRef.current;
    let cancelled = false;
    const isCurrentRun = () => !cancelled && runId === initSessionRunRef.current;

    const initSession = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const requestedConversationId =
          params.get('conversationId') || params.get('sessionId');
        const requestedDocumentId = params.get('documentId') || params.get('document');

        if (requestedConversationId) {
          await loadConversation(requestedConversationId, requestedDocumentId);
          return;
        }

        // Resume the analyst's last session if it still exists.
        let lastSessionId: string | null = null;
        try {
          lastSessionId = window.localStorage.getItem(LAST_SESSION_STORAGE_KEY);
        } catch {
          /* storage unavailable */
        }

        if (lastSessionId && !requestedDocumentId) {
          try {
            await conversationsApi.getConversationMetadata(lastSessionId);
            if (!isCurrentRun()) return;
            await loadConversation(lastSessionId);
            return;
          } catch (resumeError) {
            console.warn('Could not resume last session, starting new one:', resumeError);
            persistLastSession(null);
          }
        }

        if (!isCurrentRun()) return;
        await createNewConversation(requestedDocumentId);
      } catch (error) {
        if (!isCurrentRun()) return;
        console.error('Error initializing session:', error);
        const errorId = `system-${Date.now()}`;
        setMessagesMap(prev => ({
          ...prev,
          [errorId]: {
            id: errorId,
            sessionId: '',
            role: 'system',
            content: 'Error initializing chat session. Please refresh the page.',
            timestamp: new Date().toISOString(),
            referencedDocuments: [],
            referencedAnalyses: []
          }
        }));
      }
    };

    initSession();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sidebar interactions
  const handleSelectConversation = useCallback(
    (conversationId: string) => {
      if (!conversationId || conversationId === sessionId) return;
      loadConversation(conversationId).catch((err) => {
        console.error('Failed to switch conversation:', err);
      });
    },
    [sessionId, loadConversation]
  );

  const handleNewConversation = useCallback(() => {
    createNewConversation(selectedDocument?.metadata?.id || null).catch((err) => {
      console.error('Failed to create conversation:', err);
    });
  }, [createNewConversation, selectedDocument]);

  // Define handleAnalysisResult first, potentially wrap with useCallback if needed later
  const handleAnalysisResult = (
    result: any, // Start with any, then validate
    documentId: string,
    analysisType: string,
    userQuery?: string
  ) => {
    // Log the raw result received by the handler
    console.log("[handleAnalysisResult] Raw result received:", JSON.parse(JSON.stringify(result)));

    // Validate the result structure, especially the ID
    const validation = AnalysisResultSchema.safeParse(result);
    if (!validation.success || typeof validation.data.id !== 'string') {
      console.error(
        "Invalid analysis result structure or missing/invalid ID:", 
        result,
        validation.success ? '' : validation.error.flatten()
      );
      setAnalysisError(
        validation.success 
        ? "Analysis result ID is invalid."
        : "Received invalid analysis result structure from backend."
      );
      const errorId = `msg-${Date.now()}`;
      setMessagesMap(prev => ({
        ...prev,
        [errorId]: {
          id: errorId,
          sessionId: sessionId || '',
          role: 'system',
          content: validation.success 
            ? `Error: Analysis result for "${selectedDocument?.metadata?.filename || documentId}" has an invalid ID.`
            : `Error: Received invalid analysis result for "${selectedDocument?.metadata?.filename || documentId}".`,
          timestamp: new Date().toISOString(),
          referencedDocuments: [selectedDocument?.metadata?.id || documentId],
          referencedAnalyses: [],
        }
      }));
      return; 
    }

    const typedResult = validation.data as AnalysisResult; 

    setAnalysisResults(prevResults => {
      let updatedResults: AnalysisResult[];

      const newResultEntry: AnalysisResult = {
        id: typedResult.id, 
        documentIds: typedResult.documentIds || [],
        analysisType: typedResult.analysisType || 'unknown',
        timestamp: typedResult.timestamp || new Date().toISOString(),
        metrics: typedResult.metrics || [],
        ratios: typedResult.ratios || [],
        insights: typedResult.insights || [],
        visualizationData: typedResult.visualizationData || {},
        analysisText: typedResult.analysisText,
        citationReferences: typedResult.citationReferences,
        query: typedResult.query,
      };

      const existingIndex = prevResults.findIndex(r => 
        r.documentIds.includes(documentId) && r.analysisType === analysisType
      );
      
      if (existingIndex >= 0) {
        updatedResults = [...prevResults];
        updatedResults[existingIndex] = newResultEntry;
      } else {
        updatedResults = [...prevResults, newResultEntry];
      }
      return updatedResults; 
    });

    const isFailedAnalysis = (typedResult.id.startsWith('analysis-') || typedResult.id.startsWith('local-')) && 
                            (!typedResult.metrics || typedResult.metrics.length === 0) &&
                            (typedResult.insights && typedResult.insights.some(insight => 
                              typeof insight === 'string' && (insight.includes('Unable to perform financial analysis') || 
                              insight.includes('document does not contain structured financial data'))
                            ));
                                    
    if (isFailedAnalysis) {
      const failureInsight = typedResult.insights?.find(insight => typeof insight === 'string' && (insight.includes('Unable to perform financial analysis') || insight.includes('document does not contain structured financial data'))) || "detailed information was not found.";
      const analysisMessage = `I attempted to analyze the financial data in "${selectedDocument?.metadata?.filename || documentId}" but ${failureInsight.toLowerCase()}`;
      const messageId = `msg-${Date.now()}`;
      setMessagesMap(prev => ({
        ...prev,
        [messageId]: {
          id: messageId,
          sessionId: sessionId || '',
          role: 'system',
          content: analysisMessage,
          timestamp: new Date().toISOString(),
          referencedDocuments: [selectedDocument?.metadata?.id || documentId],
          referencedAnalyses: [],
        }
      }));
    } else {
      // SUCCESSFUL ANALYSIS: Use result.analysisText for an assistant message
      const currentAnalysisResult = typedResult;

      console.log("[handleAnalysisResult] Inspecting analysisText (pre-trim):");
      console.log("[handleAnalysisResult] typeof typedResult.analysisText: " + typeof typedResult.analysisText);
      console.log("[handleAnalysisResult] typedResult.analysisText VALUE: '" + typedResult.analysisText + "'");
      
      const detailedAnalysisContent = currentAnalysisResult.analysisText?.trim();
      console.log("[handleAnalysisResult] detailedAnalysisContent (post-trim):");
      console.log("[handleAnalysisResult] typeof detailedAnalysisContent: " + typeof detailedAnalysisContent);
      console.log("[handleAnalysisResult] detailedAnalysisContent VALUE: '" + detailedAnalysisContent + "'");
      console.log("[handleAnalysisResult] Is detailedAnalysisContent TRUTHY?: " + !!detailedAnalysisContent);

      if (detailedAnalysisContent) {
        console.log("[handleAnalysisResult] Condition 'detailedAnalysisContent' is TRUE. Setting assistant message.");
        console.log(`[handleAnalysisResult] Preparing to set message. Current Analysis ID: ${currentAnalysisResult.id}`);

        // Idempotency check using ref
        if (processedAnalysisMessageIdsRef.current.has(currentAnalysisResult.id)) {
          console.log(`[handleAnalysisResult] Ref check: Message for analysis ID ${currentAnalysisResult.id} already processed. Skipping duplicate.`);
          return; // Return from the if block, not the whole function unless appropriate
        }

        const messageContent = detailedAnalysisContent;
        const messageId = generateMessageId('assistant', messageContent);
        
        // Double-check if this messageId already exists
        if (messageId in messagesMap) {
          console.log(`[handleAnalysisResult] Message ID ${messageId} already exists. Skipping duplicate.`);
          return;
        }
        
        const newAssistantMessage: Message = {
          id: messageId,
          sessionId: sessionId || '',
          role: 'assistant',
          content: messageContent,
          timestamp: new Date().toISOString(),
          referencedDocuments: [selectedDocument?.metadata?.id || documentId],
          referencedAnalyses: [currentAnalysisResult.id],
        };

        setMessagesMap(prev => ({
          ...prev,
          [messageId]: newAssistantMessage
        }));
      } else {
        console.log("[handleAnalysisResult] Condition 'detailedAnalysisContent' is FALSE. Setting fallback system message.");
        const fallbackMessage = `Financial analysis for "${selectedDocument?.metadata?.filename || documentId}" is complete. Key findings are available in the Analysis tab, though a textual summary (detailedAnalysisContent was '${detailedAnalysisContent}') was not explicitly provided in the chat.`;
        const messageId = `msg-${Date.now()}`;
        setMessagesMap(prev => ({
          ...prev,
          [messageId]: {
            id: messageId,
            sessionId: sessionId || '',
            role: 'system',
            content: fallbackMessage,
            timestamp: new Date().toISOString(),
            referencedDocuments: [selectedDocument?.metadata?.id || documentId],
            referencedAnalyses: [currentAnalysisResult.id],
          }
        }));
      }
    }
  };

  // DISABLED: Automatic analysis on document selection
  // This useEffect was previously triggering basic_financial analysis automatically
  // when a document was selected. Now analysis must be triggered manually via buttons.
  /*
  useEffect(() => {
    const runAnalysis = async () => {
      if (!selectedDocument) {
        // console.log('[useEffect runAnalysis] No selected document, returning.');
        return;
      }

      const requestKey = `${selectedDocument.metadata.id}-basic_financial`;
      // console.log(`[useEffect runAnalysis] Generated requestKey: ${requestKey}`);

      if (analysisRequestInFlightRef.current.has(requestKey)) {
        console.log(`[useEffect runAnalysis] Analysis request ${requestKey} already in flight. Skipping.`);
        return;
      }

      // Check if analysis has already been successfully completed and results are stored
      if (analysisResults.some(result => result.documentIds.includes(selectedDocument.metadata.id) && result.analysisType === 'basic_financial')) {
        console.log(`[useEffect runAnalysis] Basic financial analysis already performed and results exist for document ${selectedDocument.metadata.id}. Skipping.`);
        return;
      }
      
      try {
        analysisRequestInFlightRef.current.add(requestKey);
        setAnalysisLoading(true);
        console.log(`[useEffect runAnalysis] Starting analysis for ${requestKey}. In-flight requests:`, Array.from(analysisRequestInFlightRef.current));

        const result = await analysisApi.runAnalysis(
          [selectedDocument.metadata.id],
          'basic_financial',
          {} // No specific parameters for basic_financial, but pass empty object
        );
        // Call the centralized handler
        handleAnalysisResult(result, selectedDocument.metadata.id, 'basic_financial');
        
      } catch (error) {
        console.error(`[useEffect runAnalysis] Error running initial analysis for ${requestKey}:`, error);
        const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred during initial analysis.';
        // Ensure selectedDocument is still valid here if error occurs late
        const docIdForError = selectedDocument ? selectedDocument.metadata.id : 'unknown_document';
        const docFilenameForError = selectedDocument ? selectedDocument.metadata.filename : 'unknown_filename';

        const errorId = `msg-error-${Date.now()}`;
        setMessagesMap(prev => ({
          ...prev,
          [errorId]: {
            id: errorId,
            sessionId: sessionId || '',
            role: 'system',
            content: `Error performing initial analysis for ${docFilenameForError}: ${errorMsg}`,
            timestamp: new Date().toISOString(),
            referencedDocuments: [docIdForError],
            referencedAnalyses: [], 
          }
        }));
        setAnalysisError(errorMsg);
      } finally {
        analysisRequestInFlightRef.current.delete(requestKey);
        setAnalysisLoading(false);
        console.log(`[useEffect runAnalysis] Finished analysis processing for ${requestKey}. In-flight requests:`, Array.from(analysisRequestInFlightRef.current));
      }
    };

    // console.log('[useEffect runAnalysis] Effect triggered. selectedDocument:', selectedDocument ? selectedDocument.metadata.id : 'null');
    runAnalysis();
  }, [selectedDocument, analysisResults, sessionId, handleAnalysisResult]); // Added analysisResults, sessionId, and handleAnalysisResult to dependencies
  */

  const handleSendMessage = async (messageText: string) => {
    if (!sessionId) {
      console.warn('No session ID available - cannot send message');
      return;
    }

    setIsLoading(true);

    // Create a stable ID for user message
    const messageId = generateMessageId('user', messageText);
    
    // Check if a message with this ID already exists
    if (messageId in messagesMap) {
      console.log(`[handleSendMessage] User message with ID ${messageId} already exists. Skipping duplicate.`);
      return;
    }
    
    const userMessage: Message = {
      id: messageId,
      sessionId: sessionId || '',
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
      referencedDocuments: selectedDocument ? [selectedDocument.metadata.id] : [],
      referencedAnalyses: [],
    };

    // Update messages map to ensure no duplicates
    setMessagesMap(prev => ({
      ...prev,
      [messageId]: userMessage
    }));

    try {
      let response;
      if (selectedDocument) {
        response = await conversationApi.sendMessage(
          sessionId, 
          messageText, 
          [selectedDocument.metadata.id]
        );
      } else {
        response = await conversationApi.sendMessage(sessionId, messageText);
      }

      // Generate stable ID for assistant response
      const responseContent = response.content || '';
      const messageId = generateMessageId('assistant', responseContent);
      
      // Check if a message with this ID already exists
      if (messageId in messagesMap) {
        console.log(`[handleSendMessage] Assistant response with ID ${messageId} already exists. Skipping duplicate.`);
        return;
      }
      
      // Add assistant response to chat map
      setMessagesMap(prev => ({
        ...prev,
        [messageId]: {
          id: messageId,
          sessionId: sessionId || '',
          role: 'assistant',
          content: responseContent,
          timestamp: new Date().toISOString(),
          referencedDocuments: response.referencedDocuments || [],
          referencedAnalyses: response.referencedAnalyses || [],
          citationLinks: response.citationLinks || [],
          analysis_blocks: response.analysisBlocks || [],
        }
      }));
    } catch (error) {
      console.error('Error sending message:', error);
      const errorId = `msg-error-${Date.now()}`;
      setMessagesMap(prev => ({
        ...prev,
        [errorId]: {
          id: errorId,
          sessionId: sessionId || '',
          role: 'system',
          content: 'Error sending message. Please try again.',
          timestamp: new Date().toISOString(),
          referencedDocuments: [],
          referencedAnalyses: [],
        }
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadSuccess = (document: ProcessedDocument) => {
    setSelectedDocument(document);
    setShowUploadForm(false);
    const messageId = `msg-${Date.now()}`;
    setMessagesMap(prev => ({
      ...prev,
      [messageId]: {
        id: messageId,
        sessionId: sessionId || '',
        role: 'system',
        content: `Document "${document.metadata.filename}" uploaded successfully. Starting analysis...`,
        timestamp: new Date().toISOString(),
        referencedDocuments: [document.metadata.id],
        referencedAnalyses: [],
      }
    }));
  };

  const handleUploadError = (error: Error) => {
    const errorId = `msg-${Date.now()}`;
    setMessagesMap(prev => ({
      ...prev,
      [errorId]: {
        id: errorId,
        sessionId: sessionId || '',
        role: 'system',
        content: `Upload failed: ${error.message}`,
        timestamp: new Date().toISOString(),
        referencedDocuments: [],
        referencedAnalyses: [],
      }
    }));
  };

  const handleCitationClick = (highlightId: string) => {
    setHighlightId(highlightId);
    setActiveTab('document');
  };

  const runManualAnalysis = async (documentId: string, analysisType: string, knowledgeBase?: string, userQuery?: string) => {
    const requestKey = JSON.stringify({
      documentId,
      analysisType,
      knowledgeBase: knowledgeBase || '',
      userQuery: userQuery || '',
    });

    if (analysisRequestInFlightRef.current.size > 0) {
      console.log(`[runManualAnalysis] Analysis request already in flight. Skipping ${requestKey}.`);
      return;
    }

    analysisRequestInFlightRef.current.add(requestKey);
    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const result = await analysisApi.runAnalysis(
        [documentId],
        analysisType,
        {}, // empty parameters object
        knowledgeBase,
        userQuery
      );

      setAnalysisResults(prevResults => {
        const analysisResultToUpdate = result as AnalysisResult;
        
        if (typeof analysisResultToUpdate.id !== 'string') {
          console.error("Analysis result ID is missing or not a string, cannot update state:", analysisResultToUpdate);
          return prevResults; 
        }

        const newResultEntry: AnalysisResult = {
          id: analysisResultToUpdate.id,
          documentIds: analysisResultToUpdate.documentIds || [],
          analysisType: analysisResultToUpdate.analysisType || 'unknown',
          timestamp: analysisResultToUpdate.timestamp || new Date().toISOString(),
          metrics: analysisResultToUpdate.metrics || [],
          ratios: analysisResultToUpdate.ratios || [],
          insights: analysisResultToUpdate.insights || [],
          visualizationData: analysisResultToUpdate.visualizationData || {},
          analysisText: analysisResultToUpdate.analysisText,
          citationReferences: analysisResultToUpdate.citationReferences,
          query: analysisResultToUpdate.query,
        };

        const existingIndex = prevResults.findIndex(r => 
          r.documentIds.includes(documentId) && r.analysisType === analysisType
        );
        
        if (existingIndex >= 0) {
          const updatedResults = [...prevResults];
          updatedResults[existingIndex] = newResultEntry;
          return updatedResults;
        }
        return [...prevResults, newResultEntry];
      });
      
      // Display analysisText in chat for manual analysis too
      const currentManualAnalysisResult = result as AnalysisResult; // Type assertion
      const detailedManualAnalysisContent = currentManualAnalysisResult.analysisText?.trim();
      if (detailedManualAnalysisContent) {
        const messageId = generateMessageId('assistant', detailedManualAnalysisContent);
        setMessagesMap(prev => ({
          ...prev,
          [messageId]: {
            id: messageId,
            sessionId: sessionId || '',
            role: 'assistant',
            content: detailedManualAnalysisContent,
            timestamp: new Date().toISOString(),
            referencedDocuments: [documentId],
            referencedAnalyses: [currentManualAnalysisResult.id],
          }
        }));
      } else {
        // Fallback system message if no analysisText
        const fallbackMessage = `I've completed the ${analysisType} analysis${userQuery ? ' for: "' + userQuery + '"' : ''}. You can see the results in the Analysis tab, though a textual summary (detailedAnalysisContent was '${detailedManualAnalysisContent}') was not explicitly provided in the chat.`;
        const messageId = `msg-${Date.now()}`;
        setMessagesMap(prev => ({
          ...prev,
          [messageId]: {
            id: messageId,
            sessionId: sessionId || '',
            role: 'system',
            content: fallbackMessage,
            timestamp: new Date().toISOString(),
            referencedDocuments: [documentId],
            referencedAnalyses: [currentManualAnalysisResult.id],
          }
        }));
      }
      
      // Switch to analysis tab to show results
      setActiveTab('analysis');
    } catch (error) {
      console.error('Error running manual analysis:', error);
      setAnalysisError(error instanceof Error ? error.message : 'Unknown error occurred');
      
      // Add error message to chat
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      const errorId = `msg-${Date.now()}`;
      setMessagesMap(prev => ({
        ...prev,
        [errorId]: {
          id: errorId,
          sessionId: sessionId || '',
          role: 'system',
          content: errorMsg,
          timestamp: new Date().toISOString(),
          referencedDocuments: [documentId],
          referencedAnalyses: [],
        }
      }));
    } finally {
      analysisRequestInFlightRef.current.delete(requestKey);
      setAnalysisLoading(false);
    }
  };

  // Memoize the message update callback to prevent re-renders
  const handleMessageUpdate = useCallback((message: Message) => {
    // A new user message kicks off backend auto-titling; refresh the sidebar
    // so the session list reflects the new title/ordering.
    if (message.role === 'user') {
      setHistoryRefreshKey((k) => k + 1);
    }
    // Add streaming message to the messages map
    setMessagesMap(prev => {
      const existingMessage = prev[message.id];

      const normalizeCitations = (citations?: Citation[]) => {
        if (!Array.isArray(citations)) return [];
        return citations
          .map((c) => ({
            id: c.id,
            highlightId: c.highlightId || '',
            page: c.startPageNumber || 0,
            rectCount: c.rects?.length || 0,
            text: (c.citedText || '').trim().toLowerCase().slice(0, 120)
          }))
          .sort((a, b) => {
            const keyA = `${a.id}|${a.highlightId}|${a.page}|${a.rectCount}|${a.text}`;
            const keyB = `${b.id}|${b.highlightId}|${b.page}|${b.rectCount}|${b.text}`;
            return keyA.localeCompare(keyB);
          });
      };

      const getAnalysisBlockFingerprint = (msg?: Message) => {
        const blocks = ((msg as any)?.analysis_blocks || (msg as any)?.analysisBlocks || []) as any[];
        return blocks
          .map((block, idx) => {
            const title = (block?.title || '').trim();
            const type = block?.visualizationType || block?.type || 'unknown';
            const tool = block?.tool_name || block?.toolName || '';
            const points = Array.isArray(block?.data) ? block.data.length : 0;
            return `${idx}:${type}:${tool}:${title}:${points}`;
          })
          .join('|');
      };
      
      // For post-viz messages, tool messages, and no-result messages, check if already exists
      if (message.id.startsWith('post_viz_') || message.id.startsWith('tool_') || message.id.startsWith('no_result_')) {
        // If message already exists with same ID, skip it
        if (existingMessage) {
          console.log(`Skipping duplicate ${message.id.split('_')[0]} message (already exists)`);
          return prev;
        }
        
        const messageType = message.id.startsWith('post_viz_') ? 'post-visualization' : 
                           message.id.startsWith('tool_') ? 'tool' : 'no-result';
        console.log(`Adding ${messageType} message: ${message.content.substring(0, 50)}...`);
        return {
          ...prev,
          [message.id]: message
        };
      }
      
      // For regular streaming messages, update whenever meaningful payload changed.
      // This avoids race conditions where websocket text updates can overwrite or
      // block later citation/analysis-block enrichment from backend polling.
      const existingCitationFingerprint = JSON.stringify(normalizeCitations(existingMessage?.citations));
      const incomingCitationFingerprint = JSON.stringify(normalizeCitations(message.citations));
      const existingAnalysisFingerprint = getAnalysisBlockFingerprint(existingMessage);
      const incomingAnalysisFingerprint = getAnalysisBlockFingerprint(message);

      const contentChanged = !!existingMessage && existingMessage.content !== message.content;
      const citationsChanged = existingCitationFingerprint !== incomingCitationFingerprint;
      const analysisChanged = existingAnalysisFingerprint !== incomingAnalysisFingerprint;

      if (!existingMessage || contentChanged || citationsChanged || analysisChanged) {
        const mergedMessage: Message = {
          ...(existingMessage || {}),
          ...message,
          // Preserve richer payloads when one side is empty; keep incoming when present.
          citations:
            Array.isArray(message.citations) && message.citations.length > 0
              ? message.citations
              : existingMessage?.citations || [],
          analysis_blocks:
            ((message as any).analysis_blocks && (message as any).analysis_blocks.length > 0)
              ? (message as any).analysis_blocks
              : ((existingMessage as any)?.analysis_blocks || [])
        };

        console.log('[handleMessageUpdate] Updating message:', {
          messageId: message.id,
          hadCitations: !!existingMessage?.citations?.length,
          nowHasCitations: !!message.citations?.length,
          citationCount: message.citations?.length || 0,
          contentChanged,
          citationsChanged,
          analysisChanged,
          analysisBlockCount: ((mergedMessage as any).analysis_blocks || []).length
        });
        return {
          ...prev,
          [message.id]: mergedMessage
        };
      }
      return prev; // No change needed
    });
  }, []);

  // Handle clicking a citation marker in the chat – switch to the document tab and
  // scroll to the related highlight (if we have its ID)
  const handleNavigateToHighlight = useCallback((citation: Citation) => {
    if (citation) {
      addCitations([citation]);
      // Use the citation ID (which might be a temp ID)
      // The PDFViewer has been updated to handle both temp IDs and UUIDs
      const navigationHighlightId = citation.highlightId || citation.id;
      console.log('[WorkspacePage] handleNavigateToHighlight:', {
        citationId: citation.id,
        highlightId: citation.highlightId,
        navigationHighlightId,
        page: citation.startPageNumber
      });
      if (typeof documentPanelRef.current?.scrollIntoView === 'function') {
        documentPanelRef.current.scrollIntoView({
          behavior: 'auto',
          block: 'start',
          inline: 'nearest',
        });
      }
      setActiveTab('document');
      setHighlightId(navigationHighlightId);
    }
  }, [addCitations]);

  return (
    <div className="workspace-page flex min-h-[calc(100dvh-72px)] flex-col overflow-x-hidden overflow-y-auto">
      <section className="workspace-overview">
        <p className="workspace-eyebrow">OP_APRT · CFIN WORKSPACE</p>
        <h1 className="workspace-title">Aperture Analysis Workspace</h1>
        <p className="workspace-description">
          Upload filings and financial statements, ask natural-language questions, and generate
          cited analysis with charts and structured outputs in one workflow.
        </p>
      </section>

      <div className="flex min-h-0 flex-1 gap-4 pb-6">
        <ConversationSidebar
          currentSessionId={sessionId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          refreshKey={historyRefreshKey}
        />

        <div className="workspace-grid grid min-h-0 flex-1 grid-cols-1 gap-4 md:grid-cols-3">
        <div className="workspace-panel col-span-1 flex min-h-0 flex-col overflow-hidden">
          <div className="workspace-panel-bar flex-shrink-0 px-4 py-3">
            <h2 className="flex items-center text-base font-avenir-pro-demi text-foreground">
              <FileSearch className="mr-2 h-5 w-5 text-primary" />
              Claude Workspace Chat
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Ask questions about the active document and jump directly to citations.
            </p>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <StreamingChatInterface
              key={sessionId || 'no-session'}
              messages={messages}
              onSendMessage={handleSendMessage}
              activeDocuments={selectedDocument ? [selectedDocument.metadata.id] : []}
              isLoading={isLoading}
              conversationId={sessionId || undefined}
              onMessageUpdate={handleMessageUpdate}
              onNavigateToHighlight={handleNavigateToHighlight}
            />
          </div>
        </div>

        <div
          ref={documentPanelRef}
          className="workspace-panel col-span-2 flex min-h-0 flex-col overflow-hidden scroll-mt-20"
        >
          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as 'document' | 'analysis')}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="workspace-tab-wrap px-3 py-2">
              <TabsList className="grid grid-cols-2 bg-transparent p-0">
                <TabsTrigger
                  value="document"
                  className="workspace-tab-trigger font-avenir-pro data-[state=active]:bg-background data-[state=active]:text-primary"
                >
                  <div className="flex items-center">
                    <FileText className="mr-1.5 h-4 w-4" />
                    Document
                  </div>
                </TabsTrigger>
                <TabsTrigger
                  value="analysis"
                  className="workspace-tab-trigger font-avenir-pro data-[state=active]:bg-background data-[state=active]:text-primary"
                >
                  <div className="flex items-center">
                    <BarChart2 className="mr-1.5 h-4 w-4" />
                    Analysis
                  </div>
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="document" className="flex min-h-0 flex-1 p-0">
              {showUploadForm ? (
                <div className="p-6">
                  <h2 className="mb-4 text-xl font-avenir-pro-demi text-foreground">Upload Document</h2>
                  <UploadForm
                    onUploadSuccess={handleUploadSuccess}
                    onUploadError={handleUploadError}
                    sessionId={sessionId || undefined}
                  />
                </div>
              ) : selectedDocument ? (
                <div className="flex h-full min-h-0 flex-1">
                  <PDFViewer
                    document={selectedDocument}
                    highlightId={highlightId}
                    extraCitations={(() => {
                      const allCitations = Array.from(citations.values())
                      const filtered = allCitations.filter(
                        (c) => c.documentId === selectedDocument?.metadata.id,
                      )
                      console.log('[workspace] PDFViewer extraCitations:', {
                        selectedDocId: selectedDocument?.metadata.id,
                        allCitations: allCitations.map((c) => ({
                          id: c.id,
                          documentId: c.documentId,
                          hasRects: c.rects?.length > 0,
                          text: c.citedText?.substring(0, 50),
                        })),
                        filtered: filtered.map((c) => ({
                          id: c.id,
                          documentId: c.documentId,
                          hasRects: c.rects?.length > 0,
                          text: c.citedText?.substring(0, 50),
                        })),
                      })
                      return filtered
                    })()}
                    onCitationCreate={(citation) => {
                      console.log('Citation created:', citation)
                    }}
                    onCitationClick={(citation) => {
                      console.log('Citation clicked:', citation)
                    }}
                  />
                </div>
              ) : (
                <div className="flex h-full items-center justify-center p-6">
                  <div className="workspace-empty-state text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/15">
                      <FileUp className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="mb-2 text-lg font-avenir-pro-demi text-foreground">
                      No document to display
                    </h3>
                    <p className="mx-auto mb-6 max-w-md text-sm text-muted-foreground">
                      Start with a filing, deck, or statement. Aperture will parse tables, trace
                      values to source pages, and prepare the workspace for analysis.
                    </p>
                    <button onClick={() => setShowUploadForm(true)} className="workspace-primary-btn">
                      <Upload className="mr-2 h-4 w-4" />
                      Upload Document
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="analysis" className="flex min-h-0 flex-1 flex-col p-0">
              <div className="flex-shrink-0">
                <AnalysisControls
                  onRunAnalysis={(analysisType, knowledgeBase, userQuery) => {
                    if (selectedDocument) {
                      runManualAnalysis(
                        selectedDocument.metadata.id,
                        analysisType,
                        knowledgeBase,
                        userQuery,
                      )
                    } else {
                      setAnalysisError('Please select a document to analyze')
                    }
                  }}
                  isLoading={analysisLoading}
                />
              </div>
              <div className="min-h-0 flex-1 overflow-hidden">
                <Canvas
                  analysisResults={analysisResults}
                  error={analysisError || undefined}
                  loading={analysisLoading}
                  onCitationClick={handleCitationClick}
                  messages={messages}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
        </div>
      </div>
    </div>
  )
}
