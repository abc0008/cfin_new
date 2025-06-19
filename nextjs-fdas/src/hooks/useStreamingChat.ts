'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '@/types';
import { conversationApi } from '@/lib/api/conversation';

export interface StreamingEvent {
  type: 'message_start' | 'text_delta' | 'tool_start' | 'tool_complete' | 
        'chart_ready' | 'table_ready' | 'metric_ready' | 'message_complete' | 'error';
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
  
  // Track streaming state
  const [toolsInProgress, setToolsInProgress] = useState<Set<string>>(new Set());
  const [completedVisualizations, setCompletedVisualizations] = useState<{
    charts: any[];
    tables: any[];
    metrics: any[];
  }>({ charts: [], tables: [], metrics: [] });

  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // Reconnection state
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second
  const maxReconnectDelay = 30000; // 30 seconds

  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    switch (event.type) {
      case 'message_start':
        setIsStreaming(true);
        setStreamingText('');
        setStreamingMessageId(event.message_id || null);
        setToolsInProgress(new Set());
        setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
        break;

      case 'text_delta':
        if (event.text) {
          setStreamingText(event.accumulated_text || '');
        }
        break;

      case 'tool_start':
        if (event.tool_id) {
          setToolsInProgress(prev => {
            const newSet = new Set(prev);
            newSet.add(event.tool_id!);
            return newSet;
          });
        }
        break;

      case 'tool_complete':
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
        setIsStreaming(false);
        setToolsInProgress(new Set());
        
        // When message is complete, fetch the updated message from database with analysis_blocks
        console.log(`Message complete for ${streamingMessageId}, fetching complete message from database`);
        
        if (streamingMessageId && streamingText) {
          // WebSocket streaming case - we have the streaming message ID
          // Fetch the complete message from database to get correct timestamp and analysis_blocks
          const fetchCompleteMessage = async () => {
            try {
              console.log(`Fetching complete message ${streamingMessageId} from database`);
              const completeMessage = await conversationApi.getMessage(streamingMessageId);
              if (completeMessage) {
                console.log(`Received complete message with ${completeMessage.analysis_blocks?.length || 0} analysis blocks`);
                // Use the complete message with proper timestamp from database
                onMessageUpdate?.(completeMessage);
              } else {
                console.warn(`Could not fetch complete message ${streamingMessageId} from database`);
                // Fallback: create temporary message with current time if database fetch fails
                const temporaryMessage: Message = {
                  id: streamingMessageId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant',
                  content: streamingText,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                };
                onMessageUpdate?.(temporaryMessage);
              }
            } catch (error) {
              console.error(`Error fetching complete message ${streamingMessageId}:`, error);
              // Fallback: create temporary message with current time if error occurs
              const temporaryMessage: Message = {
                id: streamingMessageId,
                sessionId: conversationId,
                timestamp: new Date().toISOString(),
                role: 'assistant',
                content: streamingText,
                referencedDocuments: [],
                referencedAnalyses: [],
                citations: [],
                content_blocks: null,
                analysis_blocks: []
              };
              onMessageUpdate?.(temporaryMessage);
            }
          };
          
          // Call the async function
          fetchCompleteMessage();
        } else if (event.message_id) {
          // HTTP fallback case - we have message_id in the event
          console.log(`HTTP fallback: Message complete for ${event.message_id}, fetching from database`);
          const fetchCompleteMessage = async () => {
            try {
              const completeMessage = await conversationApi.getMessage(event.message_id!);
              if (completeMessage) {
                console.log(`Received HTTP message with ${completeMessage.analysis_blocks?.length || 0} analysis blocks`);
                onMessageUpdate?.(completeMessage);
              } else {
                console.warn(`Could not fetch HTTP message ${event.message_id} from database`);
              }
            } catch (error) {
              console.error(`Error fetching HTTP message ${event.message_id}:`, error);
            }
          };
          fetchCompleteMessage();
        } else {
          console.warn('Message complete event received but no streamingMessageId or event.message_id available');
        }
        
        // Reset streaming state
        setStreamingText('');
        setStreamingMessageId(null);
        setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
        break;

      case 'error':
        setIsStreaming(false);
        setToolsInProgress(new Set());
        onError?.(event.message || event.error || 'Unknown streaming error');
        break;
    }
  }, [conversationId, streamingMessageId, streamingText, onMessageUpdate, onVisualizationReady, onError]);

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
          handleStreamingEvent(streamingEvent);
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
  }, [conversationId, handleStreamingEvent, onError, clearReconnectTimeout, getReconnectDelay]);

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
          handleStreamingEvent(streamingEvent);
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
  }, [conversationId, handleStreamingEvent]);

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
              handleStreamingEvent(streamingEvent);
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
  }, [conversationId, handleStreamingEvent]);

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