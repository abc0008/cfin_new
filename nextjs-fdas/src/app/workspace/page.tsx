'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText, BarChart2, Upload, FileUp, Zap, ChevronRight, FileSearch } from 'lucide-react'
import { ChatInterface } from '../../components/chat/ChatInterface'
import { UploadForm } from '../../components/document/UploadForm'
import dynamic from 'next/dynamic'
import { ProcessedDocument, AnalysisResult, Message } from '@/types'
import { conversationApi } from '@/lib/api/conversation'
import { analysisApi } from '@/lib/api/analysis'
import Canvas from '@/components/visualization/Canvas'
import { AnalysisControls } from '@/components/analysis/AnalysisControls'
import { AnalysisResultSchema } from '@/validation/schemas'

// Import PDFViewer component with dynamic import to avoid SSR issues
const PDFViewer = dynamic(
  () => import('../../components/document/PDFViewer').then(mod => mod.PDFViewer),
  { ssr: false }
)

export default function Workspace() {
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
  const processedAnalysisMessageIdsRef = useRef<Set<string>>(new Set());
  const analysisRequestInFlightRef = useRef<Set<string>>(new Set());
  
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

  // Initialize conversation session when component mounts
  useEffect(() => {
    let mounted = true;
    let sessionInitialized = false;

    const initSession = async () => {
      // Only create a session if we don't have one and haven't tried to initialize yet
      if (!sessionId && !sessionInitialized) {
        sessionInitialized = true;
        try {
          setIsLoading(true);
          // Create a new conversation session
          const response = await conversationApi.createConversation('New Conversation');
          if (mounted) {
            // The backend returns sessionId in camelCase due to alias_generator
            const sessionIdValue = response.sessionId || response.session_id;
            setSessionId(sessionIdValue);
            console.log('Created conversation session:', sessionIdValue);
          }
        } catch (error) {
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
        } finally {
          if (mounted) {
            setIsLoading(false);
          }
        }
      }
    };

    initSession();

    return () => {
      mounted = false;
    };
  }, []);

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
      setAnalysisLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 pt-2">
        <h1 className="text-2xl font-avenir-pro-demi text-primary mb-0">Analysis Workspace</h1>
        <p className="text-muted-foreground font-avenir-pro mb-[6px]">
          Upload financial documents, ask questions, and analyze the data through interactive visualizations.
        </p>
      </div>

      {/* Main workspace area */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4 px-4 pb-6">
        {/* Left side: Chat Interface */}
        <div className="bg-card rounded-xl shadow-md flex flex-col min-h-[calc(100vh-12rem)] overflow-auto border border-border col-span-1 flex-1">
          <div className="py-1 px-2 border-b border-border bg-muted/30 rounded-t-xl flex-shrink-0">
            <h2 className="text-base font-avenir-pro-demi text-foreground flex items-center">
              <FileSearch className="h-5 w-5 mr-2" />
              Interactive Chat
            </h2>
            <p className="text-xs text-muted-foreground font-avenir-pro">Ask questions about your financial documents</p>
          </div>
          <div className="flex-1 overflow-hidden">
            <ChatInterface 
              messages={messages} 
              onSendMessage={handleSendMessage} 
              activeDocuments={selectedDocument ? [selectedDocument.metadata.id] : []}
              isLoading={isLoading}
              conversationId={sessionId || undefined}
            />
          </div>
        </div>

        {/* Right side: Document View / Analysis */}
        <div className="bg-card rounded-xl shadow-md flex flex-col min-h-[calc(100vh-12rem)] overflow-auto border border-border col-span-2 flex-1">
          {/* Tab navigation */}
          <div className="border-b border-border bg-muted/30 rounded-t-xl">
            <Tabs defaultValue="document" className="w-full">
              <TabsList className="grid grid-cols-2 p-2 bg-transparent">
                <TabsTrigger 
                  value="document" 
                  onClick={() => setActiveTab('document')}
                  className="data-[state=active]:bg-background data-[state=active]:text-primary font-avenir-pro"
                >
                  <div className="flex items-center">
                    <FileText className="h-4 w-4 mr-1.5" />
                    Document
                  </div>
                </TabsTrigger>
                <TabsTrigger 
                  value="analysis" 
                  onClick={() => setActiveTab('analysis')}
                  className="data-[state=active]:bg-background data-[state=active]:text-primary font-avenir-pro"
                >
                  <div className="flex items-center">
                    <BarChart2 className="h-4 w-4 mr-1.5" />
                    Analysis
                  </div>
                </TabsTrigger>
              </TabsList>
              <TabsContent value="document" className="h-[calc(100vh-13rem)] p-0 flex flex-col">
                {showUploadForm ? (
                  <div className="p-6">
                    <h2 className="text-xl font-avenir-pro-demi text-primary mb-4">Upload Document</h2>
                    <UploadForm 
                      onUploadSuccess={handleUploadSuccess}
                      onUploadError={handleUploadError}
                      sessionId={sessionId || undefined}
                    />

                  </div>
                ) : selectedDocument ? (
                  <div className="h-full flex-1">
                    <PDFViewer 
                      document={selectedDocument}
                      highlightId={highlightId}
                      onCitationCreate={(citation) => {
                        console.log('Citation created:', citation);
                        // You can add citation handling logic here
                      }}
                      onCitationClick={(citation) => {
                        console.log('Citation clicked:', citation);
                        // You can add citation click handling logic here
                      }}
                    />
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center p-6 max-w-md">
                      <div className="bg-primary/10 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <FileUp className="h-8 w-8 text-primary" />
                      </div>
                      <h3 className="text-lg font-avenir-pro-demi text-primary mb-2">No document to display</h3>
                      <p className="text-muted-foreground font-avenir-pro mb-6">
                        Upload a financial document to start analyzing it with our AI-powered tools.
                      </p>
                      <button
                        onClick={() => setShowUploadForm(true)}
                        className="inline-flex items-center bg-primary text-primary-foreground px-6 py-3 rounded-lg text-sm font-avenir-pro-demi hover:bg-primary/90 transition-colors shadow-sm"
                      >
                        <Upload className="h-5 w-5 mr-2" />
                        Upload Document
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </button>
                    </div>
                  </div>
                )}
              </TabsContent>
              <TabsContent value="analysis" className="p-0 flex flex-col flex-1">
                <div className="flex-shrink-0">
                  <AnalysisControls 
                    onRunAnalysis={(analysisType, knowledgeBase, userQuery) => {
                      if (selectedDocument) {
                        runManualAnalysis(selectedDocument.metadata.id, analysisType, knowledgeBase, userQuery);
                      } else {
                        setAnalysisError('Please select a document to analyze');
                      }
                    }}
                    isLoading={analysisLoading}
                  />
                </div>
                <div className="flex-1 overflow-hidden">
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