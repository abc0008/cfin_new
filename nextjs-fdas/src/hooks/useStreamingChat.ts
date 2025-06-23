'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '@/types';
import { conversationApi } from '@/lib/api/conversation';

export interface StreamingEvent {
  type: 'message_start' | 'text_delta' | 'tool_start' | 'tool_complete' | 
        'chart_ready' | 'table_ready' | 'metric_ready' | 'message_complete' | 'content_update' | 'error';
  text?: string;
  accumulated_text?: string;
  message_id?: string;
  tool_id?: string;
  tool_name?: string;
  chart_data?: any;
  table_data?: any;
  metric_data?: any;
  success?: boolean;
  error?: string;
  message?: string;
  // Enhanced metadata for better content handling
  is_initial_content?: boolean;
  content_length?: number;
  content_preserved?: boolean;
}

export interface UseStreamingChatOptions {
  conversationId: string;
  onMessageUpdate?: (message: Message) => void;
  onVisualizationReady?: (type: 'chart' | 'table' | 'metric', data: any, index: number) => void;
  onError?: (error: string) => void;
}

export function useStreamingChat({
  conversationId,
  onMessageUpdate,
  onVisualizationReady,
  onError
}: UseStreamingChatOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // CLEAN FRONTEND SOLUTION: Separate initial streaming from post-tool content
  const [toolsStarted, setToolsStarted] = useState(false);
  const [frozenInitialText, setFrozenInitialText] = useState('');
  const [postToolMessageId, setPostToolMessageId] = useState<string | null>(null);
  const [postVisualizationText, setPostVisualizationText] = useState('');
  
  // Phase tracking to prevent state resets
  const [messagePhase, setMessagePhase] = useState<'initial' | 'tools' | 'post-tools' | 'complete' | null>(null);
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
  const [phaseTransitions, setPhaseTransitions] = useState<string[]>([]);
  
  // Track streaming state
  const [toolsInProgress, setToolsInProgress] = useState<Set<string>>(new Set());
  const [completedVisualizations, setCompletedVisualizations] = useState<{
    charts: any[];
    tables: any[];
    metrics: any[];
  }>({ charts: [], tables: [], metrics: [] });

  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // Use a ref to store the latest handler to avoid stale closures
  const handleStreamingEventRef = useRef<(event: StreamingEvent) => void>();
  
  // Reconnection state
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second
  const maxReconnectDelay = 30000; // 30 seconds

  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    // Debug logging to track state values
    if (event.type === 'tool_start' || event.type === 'message_start') {
      console.log(`🔍 State check on ${event.type}:`, {
        messagePhase,
        activeMessageId,
        streamingMessageId,
        phaseTransitions: phaseTransitions.length
      });
    }
    
    switch (event.type) {
      case 'message_start':
        const newMessageId = event.message_id;
        
        // Check if we're already processing a message
        if (activeMessageId) {
          console.log(`🛡️ IGNORING duplicate message_start (${newMessageId}) during active message ${activeMessageId}`);
          console.log(`🛡️ Current phase: ${messagePhase}, streamingText: ${streamingText.length} chars`);
          return; // Don't reset anything!
        }
        
        // First message_start of this conversation turn
        console.log(`🚀 Starting new message: ${newMessageId}`);
        setActiveMessageId(newMessageId);
        setMessagePhase('initial');
        setPhaseTransitions(['initial']);
        
        // Normal initialization
        setIsStreaming(true);
        setStreamingText('');
        setStreamingMessageId(newMessageId);
        setToolsStarted(false);
        setFrozenInitialText('');
        setPostToolMessageId(null);
        setPostVisualizationText('');
        setToolsInProgress(new Set());
        setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
        
        if (!newMessageId) {
          console.error('CRITICAL: message_start event missing message_id');
        }
        break;

      case 'text_delta':
        if (event.text) {
          if (messagePhase === 'initial') {
            // Building initial streaming message
            setStreamingText(prev => prev + event.text);
            console.log(`📝 Building initial streaming: ${streamingText.length + event.text.length} chars`);
          } else if (messagePhase === 'tools' || messagePhase === 'post-tools') {
            // After tools, accumulate post-visualization text
            if (messagePhase === 'tools') {
              setMessagePhase('post-tools');
              setPhaseTransitions(prev => [...prev, 'post-tools']);
              console.log(`📊 Transitioning to post-tools phase`);
            }
            setPostVisualizationText(prev => prev + event.text);
            console.log(`💬 Building post-visualization content: ${postVisualizationText.length + event.text.length} chars`);
          }
        }
        
        // Also handle accumulated_text for completeness
        if (event.accumulated_text) {
          setStreamingText(event.accumulated_text);
        }
        break;

      case 'content_update':
        // FIXED MESSAGE ID MANAGEMENT: Don't override established message IDs
        if (!streamingMessageId && event.message_id) {
          // Only set message ID if we don't have one established
          console.log(`Content update: Setting missing streamingMessageId to ${event.message_id}`);
          setStreamingMessageId(event.message_id);
          
          // Initialize phase if we haven't received a message_start event
          if (!messagePhase && !activeMessageId) {
            console.log(`📌 Initializing phase from content_update (no message_start received)`);
            setActiveMessageId(event.message_id);
            setMessagePhase('initial');
            setPhaseTransitions(['initial']);
            setIsStreaming(true);
          }
        } else if (streamingMessageId && event.message_id && streamingMessageId !== event.message_id) {
          // Message ID mismatch - log but don't override during streaming
          console.log(`🚨 MESSAGE ID MISMATCH: current=${streamingMessageId}, event=${event.message_id} - keeping current`);
        } else if (!event.message_id && !streamingMessageId) {
          console.warn('Content update event has no message_id and streamingMessageId is null');
        }
        
        if (event.accumulated_text) {
          // Route content based on phase (not just toolsStarted)
          if (messagePhase === 'initial' || (!messagePhase && !toolsStarted)) {
            // Initial streaming phase - update normally
            setStreamingText(event.accumulated_text);
            console.log(`📝 Initial streaming update: ${event.accumulated_text.length} chars`);
          } else if (messagePhase === 'tools' || messagePhase === 'post-tools' || toolsStarted) {
            // Tools have started - capture post-visualization content
            setPostVisualizationText(event.accumulated_text);
            console.log(`📊 Post-visualization content update: ${event.accumulated_text.length} chars`);
          }
        }
        break;

      case 'tool_start':
        console.log(`🔧 Tool started: ${event.tool_name} in phase ${messagePhase}`);
        
        if (messagePhase === 'initial' && streamingText && streamingMessageId) {
          // Complete Message 1 (initial streaming response)
          console.log(`✅ Completing initial streaming message: ${streamingText.length} chars`);
          
          const initialMessage = {
            id: streamingMessageId,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: 'assistant' as const,
            content: streamingText,
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],
            content_blocks: null,
            analysis_blocks: []
          };
          
          onMessageUpdate?.(initialMessage);
          
          // Transition to tools phase
          setMessagePhase('tools');
          setPhaseTransitions(prev => [...prev, 'tools']);
          setFrozenInitialText(streamingText);
          setToolsStarted(true);
          
          // Clear streaming for next phase but keep message ID
          setStreamingText('');
          setIsStreaming(false);
        } else {
          console.log(`⚠️ Tool started in phase ${messagePhase} - not completing initial message`);
        }
        
        // Track tool in progress
        if (event.tool_id) {
          setToolsInProgress(prev => new Set(prev).add(event.tool_id!));
          console.log(`🔧 Tool ${event.tool_name} (${event.tool_id}) in progress`);
        }
        break;

      case 'tool_complete':
        // FIXED MESSAGE ID MANAGEMENT: Don't override established message IDs
        if (!streamingMessageId && event.message_id) {
          console.log(`Tool complete: Setting missing streamingMessageId to ${event.message_id}`);
          setStreamingMessageId(event.message_id);
        } else if (streamingMessageId && event.message_id && streamingMessageId !== event.message_id) {
          console.log(`🚨 TOOL_COMPLETE MESSAGE ID MISMATCH: current=${streamingMessageId}, event=${event.message_id} - keeping current`);
        }
        
        if (event.tool_id) {
          setToolsInProgress(prev => {
            const newSet = new Set(prev);
            newSet.delete(event.tool_id!);
            return newSet;
          });
        }
        break;

      case 'chart_ready':
        if (event.chart_data) {
          setCompletedVisualizations(prev => {
            const newCharts = [...prev.charts, event.chart_data];
            onVisualizationReady?.('chart', event.chart_data, newCharts.length - 1);
            return {
              ...prev,
              charts: newCharts
            };
          });
        }
        break;

      case 'table_ready':
        if (event.table_data) {
          setCompletedVisualizations(prev => {
            const newTables = [...prev.tables, event.table_data];
            onVisualizationReady?.('table', event.table_data, newTables.length - 1);
            return {
              ...prev,
              tables: newTables
            };
          });
        }
        break;

      case 'metric_ready':
        if (event.metric_data) {
          setCompletedVisualizations(prev => {
            const newMetrics = [...prev.metrics, event.metric_data];
            onVisualizationReady?.('metric', event.metric_data, newMetrics.length - 1);
            return {
              ...prev,
              metrics: newMetrics
            };
          });
        }
        break;

      case 'message_complete':
        console.log(`🏁 Message complete in phase: ${messagePhase}`);
        setIsStreaming(false);
        setToolsInProgress(new Set());
        
        const messageIdToFetch = event.message_id || activeMessageId;
        
        if (!messageIdToFetch) {
          console.error('No message ID available for completion');
          return;
        }
        
        // Capture current state values before async operation
        const currentPhase = messagePhase;
        const currentPostVizText = postVisualizationText;
        const currentStreamingText = streamingText;
        const currentStreamingMessageId = streamingMessageId;
        const currentToolsStarted = toolsStarted;
        const currentCompletedVisualizations = { ...completedVisualizations };
        
        // Always fetch the complete message from backend
        const fetchCompleteMessage = async () => {
          try {
            const dbMessage = await conversationApi.getMessage(messageIdToFetch);
            
            if (dbMessage) {
              // Check what we need to create based on phase and content
              const hasVisualizations = dbMessage.analysis_blocks?.length > 0;
              const hasPostVizText = currentPostVizText && currentPostVizText.length > 0;
              const hasLocalVisualizations = currentCompletedVisualizations.charts.length > 0 || 
                                           currentCompletedVisualizations.tables.length > 0 || 
                                           currentCompletedVisualizations.metrics.length > 0;
              
              console.log(`📊 DB Message: ${hasVisualizations ? dbMessage.analysis_blocks.length : 0} visualizations`);
              console.log(`💬 Post-viz text: ${hasPostVizText ? currentPostVizText.length : 0} chars`);
              console.log(`📊 Local visualizations: ${currentCompletedVisualizations.charts.length} charts, ${currentCompletedVisualizations.tables.length} tables, ${currentCompletedVisualizations.metrics.length} metrics`);
              console.log(`📍 Current phase: ${currentPhase}, Tools started: ${currentToolsStarted}`);
              
              if (hasVisualizations) {
                // Message 2: Create visualization message
                const toolMessageId = `tool_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
                const toolMessage = {
                  id: toolMessageId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant' as const,
                  content: 'Analysis Visualizations',
                  referencedDocuments: dbMessage.referencedDocuments || [],
                  referencedAnalyses: dbMessage.referencedAnalyses || [],
                  citations: dbMessage.citations || [],
                  content_blocks: dbMessage.content_blocks,
                  analysis_blocks: dbMessage.analysis_blocks
                };
                
                console.log(`📊 Creating visualization message with ${dbMessage.analysis_blocks.length} items`);
                onMessageUpdate?.(toolMessage);
                
                // Message 3: Create post-visualization message if we have content
                if (hasPostVizText) {
                  const postVizMessageId = `post_viz_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
                  const postVizMessage = {
                    id: postVizMessageId,
                    sessionId: conversationId,
                    timestamp: new Date().toISOString(),
                    role: 'assistant' as const,
                    content: currentPostVizText,
                    referencedDocuments: [],
                    referencedAnalyses: [],
                    citations: [],
                    content_blocks: null,
                    analysis_blocks: []
                  };
                  
                  console.log(`💬 Creating post-visualization message: ${postVisualizationText.length} chars`);
                  onMessageUpdate?.(postVizMessage);
                }
              } else if (currentPhase === 'post-tools' && hasPostVizText && !hasVisualizations) {
                // We have post-visualization text but no visualizations in DB
                // This can happen if visualization storage failed or is delayed
                console.log(`⚠️ Post-tools phase with text but no DB visualizations - creating messages anyway`);
                
                // First check if we should create a placeholder visualization message
                if (currentToolsStarted && hasLocalVisualizations) {
                  // Create a placeholder visualization message with local data
                  const toolMessageId = `tool_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
                  const toolMessage = {
                    id: toolMessageId,
                    sessionId: conversationId,
                    timestamp: new Date().toISOString(),
                    role: 'assistant' as const,
                    content: 'Analysis Visualizations',
                    referencedDocuments: [],
                    referencedAnalyses: [],
                    citations: [],
                    content_blocks: null,
                    analysis_blocks: [] // Empty for now, frontend will use completedVisualizations
                  };
                  
                  console.log(`📊 Creating placeholder visualization message (no DB data)`);
                  onMessageUpdate?.(toolMessage);
                }
                
                // Then create the post-visualization text message
                const postVizMessageId = `post_viz_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
                const postVizMessage = {
                  id: postVizMessageId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant' as const,
                  content: currentPostVizText,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                };
                
                console.log(`💬 Creating standalone post-visualization message: ${postVisualizationText.length} chars`);
                onMessageUpdate?.(postVizMessage);
              } else if (currentPhase === 'initial' && currentStreamingText) {
                // No tools were used - complete as streaming-only message
                const finalMessage = {
                  id: currentStreamingMessageId || messageIdToFetch,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant' as const,
                  content: currentStreamingText,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                };
                
                console.log(`📝 Completing streaming-only message: ${currentStreamingText.length} chars`);
                onMessageUpdate?.(finalMessage);
              }
            }
          } catch (error) {
            console.error('Error fetching complete message:', error);
          }
        };
        
        // Call the async function and handle cleanup inside it
        fetchCompleteMessage().then(() => {
          // Clean up for next message AFTER messages are created
          console.log(`🧹 Cleaning up after phase transitions: ${phaseTransitions.join(' → ')}`);
          setActiveMessageId(null);
          setMessagePhase(null);
          setPhaseTransitions([]);
          setStreamingText('');
          setStreamingMessageId(null);
          setToolsStarted(false);
          setFrozenInitialText('');
          setPostToolMessageId(null);
          setPostVisualizationText('');
          setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
        }).catch((error) => {
          console.error('Error in message completion flow:', error);
          // Still clean up on error
          setActiveMessageId(null);
          setMessagePhase(null);
          setPhaseTransitions([]);
          setStreamingText('');
          setStreamingMessageId(null);
          setToolsStarted(false);
          setFrozenInitialText('');
          setPostToolMessageId(null);
          setPostVisualizationText('');
          setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
        });
        break;

      case 'error':
        setIsStreaming(false);
        setToolsInProgress(new Set());
        onError?.(event.message || event.error || 'Unknown streaming error');
        break;
    }
  }, [conversationId, streamingMessageId, streamingText, toolsStarted, frozenInitialText, postToolMessageId, postVisualizationText, messagePhase, activeMessageId, phaseTransitions, onMessageUpdate, onVisualizationReady, onError]);
  
  // Update the ref whenever the handler changes
  useEffect(() => {
    handleStreamingEventRef.current = handleStreamingEvent;
  }, [handleStreamingEvent]);

  // Calculate reconnection delay with exponential backoff
  const getReconnectDelay = useCallback(() => {
    const delay = Math.min(
      baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
      maxReconnectDelay
    );
    return delay + Math.random() * 1000; // Add jitter
  }, []);

  // Clear reconnection timeout
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Track if we're already connecting to prevent duplicate connections
  const isConnectingRef = useRef(false);

  // WebSocket streaming
  const connectWebSocket = useCallback(async (shouldReconnect = true) => {
    // Don't try to connect if no conversationId
    if (!conversationId) {
      console.warn('Cannot connect WebSocket without conversation ID');
      return;
    }

    // Prevent duplicate connection attempts
    if (isConnectingRef.current) {
      console.log('Already connecting, skipping duplicate connection attempt');
      return;
    }

    // Clear any existing reconnection timeout
    clearReconnectTimeout();

    // Close existing connection if any
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      console.log('Closing existing WebSocket connection');
      wsRef.current.close();
      wsRef.current = null;
      // Wait a bit for the connection to close
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
      // Mark that we're connecting
      isConnectingRef.current = true;

      // Validate conversation exists before attempting connection
      console.log('Validating conversation exists:', conversationId);
      const conversationExists = await conversationApi.checkConversationExists(conversationId);
      
      if (!conversationExists) {
        console.error('Conversation does not exist:', conversationId);
        onError?.(`Conversation ${conversationId} not found. Please refresh the page.`);
        isConnectingRef.current = false;
        return;
      }
      // Get the backend URL from environment or use default
      const backendHost = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const backendUrl = new URL(backendHost);
      
      // Determine WebSocket protocol based on backend protocol
      const protocol = backendUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // Construct WebSocket URL pointing to the backend server
      const wsUrl = `${protocol}//${backendUrl.hostname}:${backendUrl.port || (backendUrl.protocol === 'https:' ? '443' : '8000')}/ws/conversation/${conversationId}`;
      
      console.log('Starting WebSocket connection to:', wsUrl);
      console.log('Current isConnected state before connection:', isConnected);
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket onopen event fired for conversation:', conversationId);
        setIsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset reconnection attempts
        isConnectingRef.current = false; // Clear connecting flag
        console.log('WebSocket connected and isConnected set to true for conversation:', conversationId);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const streamingEvent: StreamingEvent = JSON.parse(event.data);
          // Use the ref to call the latest version of the handler
          handleStreamingEventRef.current?.(streamingEvent);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        isConnectingRef.current = false; // Clear connecting flag
        console.log('WebSocket disconnected, code:', event.code, 'reason:', event.reason);
        
        // Only attempt reconnection if:
        // 1. It wasn't a clean close (code 1000)
        // 2. We haven't exceeded max attempts
        // 3. shouldReconnect is true
        // 4. The component is still mounted (conversationId exists)
        if (
          shouldReconnect &&
          conversationId &&
          event.code !== 1000 &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          const delay = getReconnectDelay();
          console.log(`Reconnecting in ${Math.round(delay / 1000)}s (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectWebSocket(true);
          }, delay);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        // Don't trigger immediate reconnection here, let onclose handle it
      };
    } catch (error) {
      console.error('Error connecting WebSocket:', error);
      setIsConnected(false);
      isConnectingRef.current = false; // Clear connecting flag
      onError?.('Failed to establish WebSocket connection');
    }
  }, [conversationId, onError, clearReconnectTimeout, getReconnectDelay]);

  // Server-Sent Events streaming (fallback)
  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const sseUrl = `/api/conversation/${conversationId}/message/stream`;
      eventSourceRef.current = new EventSource(sseUrl);

      eventSourceRef.current.onopen = () => {
        setIsConnected(true);
        console.log('SSE connected for conversation:', conversationId);
      };

      eventSourceRef.current.onmessage = (event) => {
        try {
          const streamingEvent: StreamingEvent = JSON.parse(event.data);
          // Use the ref to call the latest version of the handler
          handleStreamingEventRef.current?.(streamingEvent);
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      };

      eventSourceRef.current.onerror = () => {
        setIsConnected(false);
        console.log('SSE error or disconnected');
      };
    } catch (error) {
      console.error('Error connecting SSE:', error);
      setIsConnected(false);
    }
  }, [conversationId]);

  // Send streaming message via WebSocket
  const sendStreamingMessage = useCallback(async (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected. Current state:', wsRef.current?.readyState);
      throw new Error('WebSocket is not connected. Need to call "accept" first.');
    }

    const message = {
      type: 'message',
      content,
      options: {
        citation_ids: [],
        referenced_documents: [],
        referenced_analyses: []
      }
    };

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      throw new Error('Failed to send message through WebSocket');
    }
  }, []);

  // Send streaming message via HTTP (fallback)
  const sendStreamingMessageHTTP = useCallback(async (content: string) => {
    try {
      const response = await fetch(`/api/conversation/${conversationId}/message/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: conversationId,
          content,
          citationLinks: [],
          referencedDocuments: [],
          referencedAnalyses: []
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const streamingEvent: StreamingEvent = JSON.parse(line.slice(6));
              // Use the ref to call the latest version of the handler
              handleStreamingEventRef.current?.(streamingEvent);
            } catch (error) {
              console.error('Error parsing SSE chunk:', error);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error in HTTP streaming:', error);
      throw error;
    }
  }, [conversationId]);

  // Auto-connect WebSocket on mount (only if conversationId is provided)
  useEffect(() => {
    let mounted = true;
    let connectTimeout: NodeJS.Timeout | null = null;

    if (conversationId && mounted) {
      // Add a small delay to debounce rapid re-renders
      connectTimeout = setTimeout(() => {
        if (mounted) {
          connectWebSocket();
        }
      }, 100);
    }

    return () => {
      mounted = false;
      
      // Clear connection timeout
      if (connectTimeout) {
        clearTimeout(connectTimeout);
      }
      
      // Clear any pending reconnection
      clearReconnectTimeout();
      
      // Clear connecting flag
      isConnectingRef.current = false;
      
      // Close WebSocket with clean close code
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
      
      // Close SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [conversationId]); // Remove connectWebSocket from deps to prevent loops

  return {
    // Connection state
    isConnected,
    isStreaming,
    
    // Streaming content
    streamingText,
    streamingMessageId,
    toolsInProgress: Array.from(toolsInProgress),
    completedVisualizations,
    
    // Clean streaming state (for debugging)
    toolsStarted,
    frozenInitialText,
    postToolMessageId,
    postVisualizationText,
    
    // Connection methods
    connectWebSocket,
    connectSSE,
    
    // Messaging methods
    sendStreamingMessage,
    sendStreamingMessageHTTP,
    
    // Manual event handling
    handleStreamingEvent
  };
}