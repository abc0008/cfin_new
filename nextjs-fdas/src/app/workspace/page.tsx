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
            content: `Error performing initial analysis for "${selectedDocument?.metadata?.filename || 'the selected document'}": ${errorMsg}`,
            timestamp: new Date().toISOString(),
            referencedDocuments: [selectedDocument.metadata.id], // selectedDocument is defined here
            referencedAnalyses: [],
          };
          return [...prev, newSystemMessage];
        });
        setAnalysisError(errorMsg); 
      } finally {
        setAnalysisLoading(false);
      }
    };
    
    if (selectedDocument && sessionId) { // Ensure sessionId is also available
      runAnalysis();
    }
  // Add handleAnalysisResult to dependencies if it's stable (e.g., memoized with useCallback)
  // For now, omitting it to prevent potential infinite loops if it's redefined on every render
  // and uses state that changes frequently. If issues arise, wrap handleAnalysisResult with useCallback.
  }, [selectedDocument, sessionId, analysisResults]);

  const handleSendMessage = async (messageText: string) => {
    if (!sessionId) {
      console.error("No valid session ID available");
      const errorMessage = {
        id: `system-${Date.now()}`,
        role: 'system',
        content: 'Error: No active session. Please refresh the page.',
        timestamp: new Date().toISOString(),
        metadata: {
          referencedDocuments: [],
          referencedAnalyses: []
        }
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    try {
      // Show user message immediately
      const userMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: messageText,
        timestamp: new Date().toISOString(),
        metadata: {
          referencedDocuments: selectedDocument ? [selectedDocument.metadata.id] : [],
          referencedAnalyses: []
        }
      };
      
      // Add the user message
      setMessages(prev => [...prev, userMessage]);
      
      // Set loading state
      setIsLoading(true);
      
      const documentIds = selectedDocument ? [selectedDocument.metadata.id] : [];
      
      // Get response from the actual API
      const response = await conversationApi.sendMessage(
        sessionId,
        messageText,
        documentIds
      );
      
      // Add the AI response to messages
      setMessages(prev => [...prev, response]);
    } catch (error) {
      console.error("Error sending message:", error);
      // Add error message to chat
      const errorMessage = {
        id: `system-${Date.now()}`,
        role: 'system',
        content: `Error sending message: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
        metadata: {
          referencedDocuments: [],
          referencedAnalyses: []
        }
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadSuccess = (document: ProcessedDocument) => {
    setSelectedDocument(document);
    setShowUploadForm(false);
    
    // Add a system message about the successful upload
    const uploadSuccessMessage = {
      id: `system-${Date.now()}`,
      sessionId: sessionId || 'demo-session',
      timestamp: new Date().toISOString(),
      role: 'system',
      content: `Successfully uploaded: ${document.metadata.filename}`,
      referencedDocuments: [document.metadata.id],
      referencedAnalyses: []
    };
    
    setMessages((prev: any) => [...prev, uploadSuccessMessage]);
  };

  const handleUploadError = (error: Error) => {
    // Add an error message to the chat
    const errorMessage = {
      id: `system-${Date.now()}`,
      sessionId: sessionId || 'demo-session',
      timestamp: new Date().toISOString(),
      role: 'system',
      content: `Error uploading document: ${error.message}`,
      referencedDocuments: [],
      referencedAnalyses: []
    };
    
    setMessages((prev: any) => [...prev, errorMessage]);
  };

  // Handle citation clicks from analysis or chat
  const handleCitationClick = (highlightId: string) => {
    setHighlightId(highlightId);
    setActiveTab('document'); // Switch to document tab to show the citation
  };

  // Add this new function to run manual analysis
  const runManualAnalysis = async (documentId: string, analysisType: string, knowledgeBase?: string, userQuery?: string) => {
    if (!documentId) return;
    
    setAnalysisLoading(true);
    setAnalysisError(null);
    
    try {
      // Setup parameters with custom knowledge base and query if provided
      const parameters: Record<string, any> = {};
      if (knowledgeBase) parameters.knowledge_base = knowledgeBase;
      if (userQuery) parameters.user_query = userQuery;
      
      const result = await analysisApi.runAnalysis(
        [documentId],
        analysisType,
        parameters
      );
      
      // Add the new result and update messages
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
    <div className="flex flex-col h-full bg-gradient-to-b from-indigo-50 to-white">
      <div className="container mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-indigo-700 mb-2">Analysis Workspace</h1>
        <p className="text-gray-600 mb-6">
          Upload financial documents, ask questions, and analyze the data through interactive visualizations.
        </p>
      </div>

      {/* Main workspace area */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 px-4 pb-6">
        {/* Left side: Chat Interface */}
        <div className="bg-white rounded-xl shadow-md flex flex-col h-[calc(100vh-180px)]">
          <div className="p-4 border-b border-gray-100 bg-indigo-50 rounded-t-xl">
            <h2 className="text-lg font-semibold text-indigo-700 flex items-center">
              <FileSearch className="h-5 w-5 mr-2" />
              Interactive Chat
            </h2>
            <p className="text-sm text-gray-600">Ask questions about your financial documents</p>
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
        <div className="bg-white rounded-xl shadow-md flex flex-col h-[calc(100vh-180px)]">
          {/* Tab navigation */}
          <div className="border-b border-gray-100 bg-indigo-50 rounded-t-xl">
            <Tabs defaultValue="document" className="w-full">
              <TabsList className="grid grid-cols-2 p-2">
                <TabsTrigger 
                  value="document" 
                  onClick={() => setActiveTab('document')}
                  className="data-[state=active]:bg-white data-[state=active]:text-indigo-700"
                >
                  <div className="flex items-center">
                    <FileText className="h-4 w-4 mr-1.5" />
                    Document
                  </div>
                </TabsTrigger>
                <TabsTrigger 
                  value="analysis" 
                  onClick={() => setActiveTab('analysis')}
                  className="data-[state=active]:bg-white data-[state=active]:text-indigo-700"
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
                    <h2 className="text-xl font-semibold text-indigo-700 mb-4">Upload Document</h2>
                    <UploadForm 
                      onUploadSuccess={handleUploadSuccess}
                      onUploadError={handleUploadError}
                      sessionId={sessionId || undefined}
                    />
                    <button
                      onClick={() => setShowUploadForm(false)}
                      className="mt-4 text-sm text-indigo-500 hover:text-indigo-700"
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
                      <div className="bg-indigo-100 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <FileUp className="h-8 w-8 text-indigo-600" />
                      </div>
                      <h3 className="text-lg font-semibold text-indigo-700 mb-2">No document to display</h3>
                      <p className="text-gray-600 mb-6">
                        Upload a financial document to start analyzing it with our AI-powered tools.
                      </p>
                      <button
                        onClick={() => setShowUploadForm(true)}
                        className="inline-flex items-center bg-indigo-600 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm"
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
                  <div className="p-4 border-b">
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