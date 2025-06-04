'use client'

import { useState, useEffect } from 'react'
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
  const [messages, setMessages] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState<ProcessedDocument | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [showReflectionsDialog, setShowReflectionsDialog] = useState(false);

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
            setSessionId(response.session_id);
            console.log('Created conversation session:', response.session_id);
          }
        } catch (error) {
          console.error('Error initializing session:', error);
          if (mounted) {
            setMessages(prev => [...prev, {
              id: `system-${Date.now()}`,
              role: 'system',
              content: 'Error initializing chat session. Please refresh the page.',
              timestamp: new Date().toISOString(),
              metadata: {
                referencedDocuments: [],
                referencedAnalyses: []
              }
            }]);
          }
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
  }, []); // Remove sessionId dependency to prevent multiple initializations

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
      setMessages(prev => {
        const newSystemMessage: Message = {
          id: `msg-${Date.now()}`,
          sessionId: sessionId,
          role: 'system',
          content: validation.success 
            ? `Error: Analysis result for "${selectedDocument?.metadata?.filename || documentId}" has an invalid ID.`
            : `Error: Received invalid analysis result for "${selectedDocument?.metadata?.filename || documentId}".`,
          timestamp: new Date().toISOString(),
          referencedDocuments: [selectedDocument?.metadata?.id || documentId],
          referencedAnalyses: [],
        };
        return [...prev, newSystemMessage];
      });
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
      setMessages(prev => {
        const newSystemMessage: Message = {
          id: `msg-${Date.now()}`,
          sessionId: sessionId,
          role: 'system',
          content: analysisMessage,
          timestamp: new Date().toISOString(),
          referencedDocuments: [selectedDocument?.metadata?.id || documentId],
          referencedAnalyses: [],
        };
        return [...prev, newSystemMessage];
      });
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
        const messageContent = `[FROM IF-BLOCK]: ${detailedAnalysisContent}`;
        setMessages(prev => {
          const newAssistantMessage: Message = {
            id: `msg-${Date.now()}`,
            sessionId: sessionId,
            role: 'assistant',
            content: messageContent,
            timestamp: new Date().toISOString(),
            referencedDocuments: [selectedDocument?.metadata?.id || documentId],
            referencedAnalyses: [currentAnalysisResult.id],
          };
          return [...prev, newAssistantMessage];
        });
      } else {
        console.log("[handleAnalysisResult] Condition 'detailedAnalysisContent' is FALSE. Setting fallback system message.");
        const fallbackMessage = `Financial analysis for "${selectedDocument?.metadata?.filename || documentId}" is complete. Key findings are available in the Analysis tab, though a textual summary (detailedAnalysisContent was '${detailedAnalysisContent}') was not explicitly provided in the chat.`;
        setMessages(prev => {
          const newSystemMessage: Message = {
            id: `msg-${Date.now()}`,
            sessionId: sessionId,
            role: 'system',
            content: fallbackMessage,
            timestamp: new Date().toISOString(),
            referencedDocuments: [selectedDocument?.metadata?.id || documentId],
            referencedAnalyses: [currentAnalysisResult.id],
          };
          return [...prev, newSystemMessage];
        });
      }
    }
  };

  // Run financial analysis when a document is selected
  useEffect(() => {
    const runAnalysis = async () => {
      if (!selectedDocument) return;
      
      if (analysisResults.some(result => result.documentIds.includes(selectedDocument.metadata.id) && result.analysisType === 'basic_financial')) {
        console.log('Basic financial analysis already performed for this document');
        return;
      }
      
      setAnalysisLoading(true);
      
      try {
        const result = await analysisApi.runAnalysis(
          [selectedDocument.metadata.id],
          'basic_financial',
          {} // No specific parameters for basic_financial, but pass empty object
        );
        // Call the centralized handler
        handleAnalysisResult(result, selectedDocument.metadata.id, 'basic_financial');
        
      } catch (error) {
        console.error('Error running initial analysis in useEffect:', error);
        const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred during initial analysis.';
        setMessages(prev => {
          const newSystemMessage: Message = {
            id: `msg-${Date.now()}`,
            sessionId: sessionId,
            role: 'system',
            content: `Error performing initial analysis: ${errorMsg}`,
            timestamp: new Date().toISOString(),
            referencedDocuments: [selectedDocument.metadata.id],
            referencedAnalyses: [],
          };
          return [...prev, newSystemMessage];
        });
        setAnalysisError(errorMsg);
      } finally {
        setAnalysisLoading(false);
      }
    };

    runAnalysis();
  }, [selectedDocument]);

  const handleSendMessage = async (messageText: string) => {
    if (!sessionId) {
      console.warn('No session ID available - cannot send message');
      return;
    }

    setIsLoading(true);

    // Immediately add user message to chat
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      sessionId: sessionId,
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
      referencedDocuments: selectedDocument ? [selectedDocument.metadata.id] : [],
      referencedAnalyses: [],
    };

    setMessages(prev => [...prev, userMessage]);

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

      // Add assistant response to chat
      setMessages(prev => [...prev, {
        id: `msg-${Date.now()}`,
        sessionId: sessionId,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        referencedDocuments: response.referenced_documents || [],
        referencedAnalyses: response.referenced_analyses || [],
        citationReferences: response.citation_references || [],
        analysis_blocks: response.analysis_blocks || [],
      }]);

    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: `msg-${Date.now()}`,
        sessionId: sessionId,
        role: 'system',
        content: 'Error sending message. Please try again.',
        timestamp: new Date().toISOString(),
        referencedDocuments: [],
        referencedAnalyses: [],
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadSuccess = (document: ProcessedDocument) => {
    setSelectedDocument(document);
    setShowUploadForm(false);
    setMessages(prev => [...prev, {
      id: `msg-${Date.now()}`,
      sessionId: sessionId,
      role: 'system',
      content: `Document "${document.metadata.filename}" uploaded successfully. Starting analysis...`,
      timestamp: new Date().toISOString(),
      referencedDocuments: [document.metadata.id],
      referencedAnalyses: [],
    }]);
  };

  const handleUploadError = (error: Error) => {
    setMessages(prev => [...prev, {
      id: `msg-${Date.now()}`,
      sessionId: sessionId,
      role: 'system',
      content: `Upload failed: ${error.message}`,
      timestamp: new Date().toISOString(),
      referencedDocuments: [],
      referencedAnalyses: [],
    }]);
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
        { knowledgeBase, userQuery }
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
        setMessages(prev => {
          const newAssistantMessage: Message = {
            id: `msg-${Date.now()}`,
            sessionId: sessionId,
            role: 'assistant',
            content: detailedManualAnalysisContent,
            timestamp: new Date().toISOString(),
            referencedDocuments: [documentId],
            referencedAnalyses: [currentManualAnalysisResult.id],
          };
          return [...prev, newAssistantMessage];
        });
      } else {
        // Fallback system message if no analysisText
        setMessages(prev => {
          const newSystemMessage: Message = {
            id: `msg-${Date.now()}`,
            sessionId: sessionId,
            role: 'system',
            content: `I've completed the ${analysisType} analysis${userQuery ? ' for: "' + userQuery + '"' : ''}. You can see the results in the Analysis tab. A textual summary was not generated for direct chat display.`,
            timestamp: new Date().toISOString(),
            referencedDocuments: [documentId],
            referencedAnalyses: [currentManualAnalysisResult.id],
          };
          return [...prev, newSystemMessage];
        });
      }
      
      // Switch to analysis tab to show results
      setActiveTab('analysis');
    } catch (error) {
      console.error('Error running manual analysis:', error);
      setAnalysisError(error instanceof Error ? error.message : 'Unknown error occurred');
      
      // Add error message to chat
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      setMessages(prev => {
        const newSystemMessage: Message = {
          id: `msg-${Date.now()}`,
          sessionId: sessionId,
          role: 'system',
          content: `Error performing analysis: ${errorMsg}`,
          timestamp: new Date().toISOString(),
          referencedDocuments: [documentId],
          referencedAnalyses: [],
        };
        return [...prev, newSystemMessage];
      });
    } finally {
      setAnalysisLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-0">
        <h1 className="text-2xl font-avenir-pro-demi text-primary mb-2">Analysis Workspace</h1>
        <p className="text-muted-foreground font-avenir-pro mb-6">
          Upload financial documents, ask questions, and analyze the data through interactive visualizations.
        </p>
      </div>

      {/* Main workspace area */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4 px-4 pb-6">
        {/* Left side: Chat Interface */}
        <div className="bg-card rounded-xl shadow-md flex flex-col min-h-[calc(100vh-12rem)] overflow-auto border border-border col-span-1 flex-1">
          <div className="py-1 px-2 border-b border-border bg-muted/30 rounded-t-xl">
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
              <TabsContent value="document" className="h-[calc(100vh-13rem)] p-0">
                {showUploadForm ? (
                  <div className="p-6">
                    <h2 className="text-xl font-avenir-pro-demi text-primary mb-4">Upload Document</h2>
                    <UploadForm 
                      onUploadSuccess={handleUploadSuccess}
                      onUploadError={handleUploadError}
                      sessionId={sessionId || undefined}
                    />
                    <button
                      onClick={() => setShowUploadForm(false)}
                      className="mt-4 text-sm text-muted-foreground hover:text-foreground font-avenir-pro transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : selectedDocument ? (
                  <div className="h-full">
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
              <TabsContent value="analysis" className="h-[calc(100vh-13rem)] p-0 flex flex-col">
                {selectedDocument && (
                  <div className="p-4 border-b border-border">
                    <AnalysisControls 
                      isLoading={analysisLoading}
                      onRunAnalysis={(analysisType, knowledgeBase, userQuery) => {
                        runManualAnalysis(
                          selectedDocument.metadata.id,
                          analysisType,
                          knowledgeBase,
                          userQuery
                        );
                      }}
                    />
                  </div>
                )}
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