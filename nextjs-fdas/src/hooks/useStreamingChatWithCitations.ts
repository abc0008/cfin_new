'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, Citation } from '@/types';
import { ClaudeCitation } from '@/types/citation';
import { conversationApi } from '@/lib/api/conversation';
import { useCitation } from '@/context/CitationContext';
import { handleStreamingCitation } from '@/lib/pdf/citationService';

export interface StreamingEvent {
  type: 'message_start' | 'new_message_start' | 'text_delta' | 'tool_start' | 'tool_complete' | 
        'chart_ready' | 'table_ready' | 'metric_ready' | 'message_complete' | 
        'content_update' | 'error' | 'citations_delta' | 'content_block_delta';
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
  citations?: ClaudeCitation[];
  citation?: ClaudeCitation;
  content_blocks?: any[];
  block_index?: number;
  // Enhanced metadata for better content handling
  is_initial_content?: boolean;
  is_post_tools?: boolean;
  is_post_visualization?: boolean;
  content_length?: number;
  content_preserved?: boolean;
  post_tool_text?: string;
  role?: string;
  analysis_blocks?: any[];
}

export interface UseStreamingChatOptions {
  conversationId: string;
  onMessageUpdate?: (message: Message) => void;
  onVisualizationReady?: (type: 'chart' | 'table' | 'metric', data: any, index: number) => void;
  onError?: (error: string) => void;
  documentMap?: Map<number, string>; // Maps document indices to document IDs
}

export function useStreamingChatWithCitations({
  conversationId,
  onMessageUpdate,
  onVisualizationReady,
  onError,
  documentMap = new Map()
}: UseStreamingChatOptions) {
  const { addCitations } = useCitation();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // Citation tracking
  const [pendingCitations, setPendingCitations] = useState<Map<number, Citation[]>>(new Map());
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  const [citationCounter, setCitationCounter] = useState(1);
  
  // ... (rest of the original useStreamingChat state variables)
  const [toolsStarted, setToolsStarted] = useState(false);
  
  // WebSocket and streaming state
  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // Reconnection state
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second
  const maxReconnectDelay = 30000; // 30 seconds
  
  // Track if we're already connecting to prevent duplicate connections
  const isConnectingRef = useRef(false);
  const [frozenInitialText, setFrozenInitialText] = useState('');
  const [postToolMessageId, setPostToolMessageId] = useState<string | null>(null);
  const [postVisualizationText, setPostVisualizationText] = useState('');
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

  // After we receive message_complete for the initial streaming message (with toolsStarted=true)
  // we may still get follow-up text for a narrative summary. The backend SHOULD send
  // a `new_message_start` event first, but today it often does not. When that happens we
  // set this flag so the *very next* text_delta will automatically create a brand-new
  // assistant message for the post-visualization narrative.
  const [awaitingPostVisualization, setAwaitingPostVisualization] = useState(false);

  const handleStreamingEventRef = useRef<(event: StreamingEvent) => void>();
  const vizCreatedRef = useRef(false);
  const postVizCreatedRef = useRef(false);
  const lastCompletedMessageIdRef = useRef<string | null>(null);
  const dbFetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const streamingTextRef = useRef('');
  const frozenInitialTextRef = useRef('');

  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    switch (event.type) {
      case 'message_start':
        const newMessageId = event.message_id;
        
        if (activeMessageId) {
          console.log(`⚠️ Ignoring message_start - already have active message: ${activeMessageId}`);
          return;
        }
        
        setActiveMessageId(newMessageId || null);
        setMessagePhase('initial');
        setPhaseTransitions(['initial']);
        setStreamingMessageId(newMessageId || null);
        setIsStreaming(true);
        setStreamingText('');
        setFrozenInitialText('');
        setPostVisualizationText('');
        setToolsStarted(false);
        setPostToolMessageId(null);
        vizCreatedRef.current = false;
        postVizCreatedRef.current = false;
        setPendingCitations(new Map());
        setCitationCounter(1);
        setCurrentBlockIndex(0);
        break;

      case 'new_message_start':
        // Handle new message for post-visualization content
        if (event.is_post_visualization && onMessageUpdate) {
          const postVizMessage: Message = {
            id: event.message_id || `post-viz-${Date.now()}`,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: (event.role as 'assistant' | 'user' | 'system') || 'assistant',
            content: '',  // Will be filled by subsequent text_delta events
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],
            content_blocks: null,
            analysis_blocks: []
          };
          
          // Add the new message to the chat
          onMessageUpdate(postVizMessage);
          
          // Set up state for streaming this new message
          setActiveMessageId(event.message_id || null);
          setPostToolMessageId(event.message_id || null);  // Use separate state for post-viz message
          setIsStreaming(true);
          setPostVisualizationText('');  // Reset post-viz text, not streamingText
          setMessagePhase('post-tools');
        }
        break;

      case 'text_delta':
        if (!event.text) return;
        
        // Check if this text contains citation markers (e.g., [1], [2], etc.)
        const containsCitationMarkers = /\[\d+\]/.test(event.text);
        
        // 1) If this text belongs to a *known* post-viz message, append to it.
        if (event.message_id && event.message_id === postToolMessageId && onMessageUpdate) {
          // This is for the post-viz message, update it directly
          setPostVisualizationText(prev => {
            const newContent = prev + event.text;
            
            // Schedule the message update for after the state update
            setTimeout(() => {
              const updatedMessage: Message = {
                id: event.message_id,
                sessionId: conversationId,
                timestamp: new Date().toISOString(),
                role: 'assistant',
                content: newContent,
                referencedDocuments: [],
                referencedAnalyses: [],
                citations: [],
                content_blocks: null,
                analysis_blocks: []
              };
              onMessageUpdate(updatedMessage);
            }, 0);
            
            return newContent;
          });
        }
        // 2) If tools have finished (toolsStarted === true) *and* we never saw a `new_message_start`
        //    (or the flag was not set by the backend) we still need to create a fresh message for
        //    the narrative that follows the visualisations. We use either the backend-supplied
        //    message_id (if present and different from the initial one) or generate our own.
        else if ((awaitingPostVisualization || (toolsStarted && !postToolMessageId)) && !postVizCreatedRef.current) {
          const newPostVizId = event.message_id && event.message_id !== streamingMessageId
            ? event.message_id
            : `post-viz-${Date.now()}`;
          setPostToolMessageId(newPostVizId);
          setMessagePhase('post-tools');
          setPhaseTransitions(prev => [...prev, 'post-tools']);

          // Seed the new message with the first text chunk
          const initialContent = event.text;
          const postVizMessage: Message = {
            id: newPostVizId,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: 'assistant',
            content: initialContent,
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],
            content_blocks: null,
            analysis_blocks: []
          };
          if (onMessageUpdate) onMessageUpdate(postVizMessage);
          setPostVisualizationText(initialContent);
          // We successfully started the post-viz message; clear the awaiting flag so subsequent
          // deltas just append.
          setAwaitingPostVisualization(false);
          postVizCreatedRef.current = true;
        }
        // 3) Normal initial streaming text handling
        else if (messagePhase === 'initial' && !toolsStarted) {
          appendToStreamingText(event.text);
        }
        // 4) Additional chunks for the already bootstrapped post-viz message
        else if (messagePhase === 'post-tools') {
          // Handle post-tool text_delta for the post-viz message
          setPostVisualizationText(prev => {
            const newContent = prev + event.text;
            
            // Update the post-viz message
            if (postToolMessageId && onMessageUpdate) {
              setTimeout(() => {
                const updatedMessage: Message = {
                  id: postToolMessageId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant',
                  content: newContent,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                };
                onMessageUpdate(updatedMessage);
              }, 0);
            }
            
            return newContent;
          });
        } else if (containsCitationMarkers) {
          // Handle late citation markers that arrive after streaming completes
          // This happens when citations come from final_message
          console.log('Late citation markers detected:', event.text);
          
          if (toolsStarted) {
            // IMPORTANT: Citation markers belong to the initial message, not post-viz
            // Update the frozen initial text with citation markers
            appendToFrozenInitial(event.text);
            // Also update streaming text to show citations immediately
            appendToStreamingText(event.text);
          } else {
            // Append to initial streaming text if no tools were used
            appendToStreamingText(event.text);
          }
        }
        // --- 0. Explicit post-tool flag handling (some backends set is_post_tools on text_delta) ---
        if (event.is_post_tools && messagePhase !== 'post-tools') {
          // If we haven't bootstrapped a post-viz message yet, do so now.
          const newId = postToolMessageId || `post-viz-${Date.now()}`;
          if (!postToolMessageId) {
            setPostToolMessageId(newId);
          }
          setMessagePhase('post-tools');
          setPhaseTransitions(prev => prev.includes('post-tools') ? prev : [...prev, 'post-tools']);
          postVizCreatedRef.current = true;
          setAwaitingPostVisualization(false);

          const seedContent = event.text;
          setPostVisualizationText(seedContent);
          if (onMessageUpdate) {
            onMessageUpdate({
              id: newId,
              sessionId: conversationId,
              timestamp: new Date().toISOString(),
              role: 'assistant',
              content: seedContent,
              referencedDocuments: [],
              referencedAnalyses: [],
              citations: [],
              content_blocks: null,
              analysis_blocks: []
            });
          }
          return; // handled
        }
        break;

      case 'content_block_delta':
        if (event.block_index !== undefined) {
          setCurrentBlockIndex(event.block_index);
        }
        break;

      case 'citations_delta':
        if (event.citation && event.block_index !== undefined) {
          handleStreamingCitation(
            { type: 'citations_delta', citation: event.citation },
            event.block_index,
            pendingCitations,
            documentMap
          );
          
          // Update citation counter for display
          setCitationCounter(prev => prev + 1);
          
          // Opportunistically inject the marker into the visible streaming text **immediately**
          const marker = `[${citationCounter}]`;
          const citedSnippet = event.citation.cited_text || '';
          if (citedSnippet && !streamingTextRef.current.includes(marker)) {
            // Try to insert right after the cited snippet (case-insensitive)
            const escaped = citedSnippet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(escaped, 'i');
            let updated = streamingTextRef.current;
            if (regex.test(updated)) {
              updated = updated.replace(regex, (match) => `${match}${marker}`);
            } else {
              // Fallback: append to the end
              updated = `${updated}${marker}`;
            }
            setStreamingFromAccumulated(updated);
            if (messagePhase === 'tools') {
              setFrozenInitial(updated); // keep frozen copy in sync
            }
          }
        }
        break;

      case 'content_update':
        if (event.accumulated_text) {
          // If this belongs to the post-visualisation narrative treat it similarly to text_delta logic.
          if (event.is_post_tools) {
            const text = event.accumulated_text;

            // If we already have a post-viz message ID, just update that message
            if (postToolMessageId && messagePhase === 'post-tools') {
              setPostVisualizationText(text);
              if (onMessageUpdate) {
                onMessageUpdate({
                  id: postToolMessageId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant',
                  content: text,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                });
              }
            } else {
              // Otherwise bootstrap a fresh post-viz message now
              const newId = `post-viz-${Date.now()}`;
              setPostToolMessageId(newId);
              setMessagePhase('post-tools');
              setPhaseTransitions(prev => [...prev, 'post-tools']);
              setAwaitingPostVisualization(false);
              postVizCreatedRef.current = true;
              setPostVisualizationText(text);
              if (onMessageUpdate) {
                onMessageUpdate({
                  id: newId,
                  sessionId: conversationId,
                  timestamp: new Date().toISOString(),
                  role: 'assistant',
                  content: text,
                  referencedDocuments: [],
                  referencedAnalyses: [],
                  citations: [],
                  content_blocks: null,
                  analysis_blocks: []
                });
              }
            }
            return; // We've handled the post-tool update
          }

          // For the initial assistant answer we now accept updates in *both* the "initial" and
          // "tools" phases because citation markers often arrive while tools are running.

          const currentLength = streamingTextRef.current.length;
          const newLength = event.accumulated_text.length;
          const updateHasCitationMarkers = /\[\d+\]/.test(event.accumulated_text);
          const currentHasCitationMarkers = /\[\d+\]/.test(streamingTextRef.current);

          // If the update would REMOVE citation markers we already have, ignore it.
          if (!updateHasCitationMarkers && currentHasCitationMarkers) {
            console.log('Skipping content_update – would remove existing citation markers');
            return;
          }

          // Skip micro-updates that don't introduce citations or meaningful new text
          if (!updateHasCitationMarkers && newLength > currentLength && newLength - currentLength < 20 && currentLength > 100) {
            console.log('Skipping content_update – minor diff with no citations');
            return;
          }

          // Apply the accumulated text to both streaming & frozen refs so downstream logic sees it
          setStreamingFromAccumulated(event.accumulated_text);
          if (messagePhase !== 'initial') {
            // Keep frozen copy in sync when we're already in the tools phase
            setFrozenInitial(event.accumulated_text);
          }
        }
        break;

      case 'tool_start':
        if (messagePhase === 'initial' && streamingText) {
          setMessagePhase('tools');
          setPhaseTransitions(prev => [...prev, 'tools']);
          setFrozenInitial(streamingTextRef.current);
          setToolsStarted(true);
          // Don't clear streamingText here - keep it visible during tool execution
          // setIsStreaming(false); // Also keep streaming state
        }
        
        if (event.tool_id) {
          setToolsInProgress(prev => new Set(prev).add(event.tool_id!));
        }
        break;

      case 'message_complete':
        console.log('Message complete - processing citations');
        
        // Check if this is a post-visualization message completion
        if (event.is_post_visualization) {
          // For post-viz messages, just reset streaming state
          setIsStreaming(false);
          setPostVisualizationText(''); // Clear post-viz text, not streamingText
          setActiveMessageId(null);
          setPostToolMessageId(null);
          lastCompletedMessageIdRef.current = event.message_id || null;
          return;
        }
        
        // Collect all citations from both pending and event
        const allCitations: Citation[] = [];
        
        // First, get citations from pending (collected during streaming)
        pendingCitations.forEach(citations => {
          allCitations.push(...citations);
        });
        
        // Then, add any citations from the event itself (if backend provides them)
        if (event.citations && Array.isArray(event.citations)) {
          console.log(`Message complete event includes ${event.citations.length} citations from backend`);
          event.citations.forEach((citation: any) => {
            // Avoid duplicates by checking if we already have this citation
            const exists = allCitations.some(c => 
              c.startPageNumber === citation.start_page_number && 
              c.citedText === citation.cited_text
            );
            if (!exists) {
              allCitations.push({
                id: citation.id || `citation-${Date.now()}-${Math.random()}`,
                messageId: streamingMessageId || '',
                documentId: citation.document_id || '',
                documentTitle: citation.document_title || '',
                citedText: citation.cited_text || '',
                analysisId: citation.analysis_id || null,
                startPageNumber: citation.start_page_number,
                endPageNumber: citation.end_page_number,
                startCharIndex: citation.start_char_index,
                endCharIndex: citation.end_char_index,
                highlightId: `hl-${Date.now()}-${Math.random()}`,
                type: 'page_location',
                rects: []
              });
            }
          });
        }
        
        if (allCitations.length > 0) {
          console.log(`Adding ${allCitations.length} total citations to context`);
          addCitations(allCitations);
        }
        
        // Build the complete message from streaming data
        // We already have everything we need from streaming, including citation markers
        if (onMessageUpdate && streamingMessageId) {
          // Build final content - use the most up-to-date content available
          const currentStreaming = streamingTextRef.current;
          const currentFrozen = frozenInitialTextRef.current;
          const streamingHasCitations = /\[\d+\]/.test(currentStreaming);
          const frozenHasCitations = /\[\d+\]/.test(currentFrozen);
          let finalContent = '';

          // 1. Prefer whichever version actually contains citation markers
          if (streamingHasCitations && !frozenHasCitations) {
            finalContent = currentStreaming;
          } else if (frozenHasCitations && !streamingHasCitations) {
            finalContent = currentFrozen;
          } else {
            // 2. If both (or neither) have citations, choose the longer unless tools never ran
            if (toolsStarted) {
              finalContent = currentStreaming.length >= currentFrozen.length ? currentStreaming : currentFrozen;
            } else {
              // No tools – streaming text is authoritative
              finalContent = currentStreaming;
            }
          }
          
          // If we somehow still lack citation markers but have citation data, attempt to inject
          // them heuristically. We append markers immediately after the first occurrence of
          // each citedText snippet (case-insensitive) and fall back to appending at the end if
          // not found. This guarantees the superscript links appear in the UI even when the
          // backend omits the marker tokens.
          if (!/\[\d+\]/.test(finalContent) && allCitations.length > 0) {
            let workingContent = finalContent;
            allCitations.forEach((cit, idx) => {
              const marker = `[${idx + 1}]`;
              // Escape RegExp special chars in citedText
              const escaped = cit.citedText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              const regex = new RegExp(escaped, 'i');
              if (regex.test(workingContent) && !workingContent.includes(marker)) {
                workingContent = workingContent.replace(regex, (match) => `${match}${marker}`);
              } else if (!workingContent.includes(marker)) {
                // Fallback: append marker at the end
                workingContent += ` ${marker}`;
              }
            });
            finalContent = workingContent;
          }
          
          // -------- De-duplicate trailing unformatted restatement --------
          const deduplicate = (content: string): string => {
            // Heuristic: split by double newline, check if last block is large and largely contained in previous blocks (plain-text) – if so, drop it.
            const blocks = content.split(/\n{2,}/);
            if (blocks.length < 2) return content;
            const last = blocks[blocks.length - 1].trim();
            if (last.length < 200) return content;
            const plain = (s: string) => s.replace(/\[\d+\]/g, '').replace(/\s+/g, ' ').trim();
            const lastPlain = plain(last).slice(0, 120);
            const prevPlain = plain(blocks.slice(0, -1).join(' '));
            if (prevPlain.includes(lastPlain)) {
              return blocks.slice(0, -1).join('\n\n').trim();
            }
            return content;
          };
          finalContent = deduplicate(finalContent);
          
          // Log the final content for debugging
          console.log('Final streamed content:', {
            toolsStarted,
            frozenInitialTextLength: currentFrozen.length,
            postVisualizationTextLength: postVisualizationText.length,
            streamingTextLength: currentStreaming.length,
            finalContentLength: finalContent.length,
            hasAnalysisBlocks: event.analysis_blocks && event.analysis_blocks.length > 0
          });
          
          const message: Message = {
            id: streamingMessageId,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: 'assistant',
            content: finalContent,
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: allCitations,
            content_blocks: event.content_blocks || [],
            analysis_blocks: event.analysis_blocks || []  // Get from streaming event if available
          };
          
          // First, send the streamed message immediately
          onMessageUpdate(message);
          
          // Then, only fetch from database if we have tools but no analysis_blocks
          // This ensures we get the analysis blocks that were stored after streaming
          // The backend now sends analysis_blocks in the message_complete event
          if (toolsStarted && (!event.analysis_blocks || event.analysis_blocks.length === 0)) {
            console.log('Tools were used but no analysis blocks in event, fetching from database...');
            
            // Cancel any existing fetch timeout to debounce
            if (dbFetchTimeoutRef.current) {
              clearTimeout(dbFetchTimeoutRef.current);
            }
            
            // Add a small delay to ensure backend has finished storing analysis blocks
            dbFetchTimeoutRef.current = setTimeout(() => {
              import('@/lib/api/conversations').then(({ conversationsApi }) => {
                conversationsApi.getConversationHistory(conversationId, 10)
                  .then(messages => {
                    // Find our message by ID
                    const updatedMessage = messages.find(msg => msg.id === streamingMessageId);
                    if (updatedMessage && updatedMessage.analysis_blocks && updatedMessage.analysis_blocks.length > 0) {
                      console.log(`Fetched ${updatedMessage.analysis_blocks.length} analysis blocks from database`);
                      
                      // Only update the analysis blocks, keep the streamed content with citation markers
                      const enhancedMessage: Message = {
                        ...message,  // Keep all streamed data including content with citation markers
                        analysis_blocks: updatedMessage.analysis_blocks
                      };
                      
                      onMessageUpdate(enhancedMessage);
                    } else {
                      console.log('No analysis blocks found in database message');
                    }
                  })
                  .catch(error => {
                    console.error('Error fetching analysis blocks:', error);
                    // Keep using the streamed message with citations on error
                    // Citations were already collected during streaming and are preserved
                    console.log('Keeping streamed message with', message.citations?.length || 0, 'citations');
                  })
                  .finally(() => {
                    dbFetchTimeoutRef.current = null;
                  });
              });
            }, 500); // Small delay to ensure backend has finished processing
          }
        }
        
        // Reset state
        setIsStreaming(false);
        setStreamingText('');
        setActiveMessageId(null);
        setMessagePhase('complete');
        lastCompletedMessageIdRef.current = streamingMessageId;

        // If tools were used we expect a follow-up narrative. If the backend does *not* emit a
        // new_message_start we will catch the first subsequent text_delta and create the message
        // ourselves.
        if (toolsStarted) {
          setAwaitingPostVisualization(true);
        }
        break;

      // ... (other cases remain the same)
      default:
        break;
    }
  }, [messagePhase, toolsStarted, streamingText, frozenInitialText, activeMessageId, 
      streamingMessageId, postToolMessageId, conversationId, onMessageUpdate, pendingCitations, 
      documentMap, addCitations, awaitingPostVisualization]);

  // ... (rest of the hook implementation remains the same)
  
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
      
      // Clear database fetch timeout
      if (dbFetchTimeoutRef.current) {
        clearTimeout(dbFetchTimeoutRef.current);
        dbFetchTimeoutRef.current = null;
      }
      
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

  // Helper functions (hoisted) to keep refs and state in sync
  function appendToStreamingText(delta: string) {
    streamingTextRef.current += delta;
    setStreamingText(prev => prev + delta);
  }
  function setStreamingFromAccumulated(text: string) {
    streamingTextRef.current = text;
    setStreamingText(text);
  }
  function appendToFrozenInitial(delta: string) {
    frozenInitialTextRef.current += delta;
    setFrozenInitialText(prev => prev + delta);
  }
  function setFrozenInitial(text: string) {
    frozenInitialTextRef.current = text;
    setFrozenInitialText(text);
  }

  // Return the same interface as the original hook
  return {
    // Connection state
    isConnected,
    isStreaming,
    
    // Streaming content - don't concatenate post-viz text as it's a separate message
    streamingText: streamingText,
    streamingMessageId,
    toolsInProgress: Array.from(toolsInProgress),
    completedVisualizations,
    
    // Citations
    streamingCitations: Array.from(pendingCitations.values()).flat(),
    
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