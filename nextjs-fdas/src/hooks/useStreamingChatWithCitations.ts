'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, Citation } from '@/types';
import { ClaudeCitation } from '@/types/citation';
import { conversationApi } from '@/lib/api/conversation';
import { useCitation } from '@/context/CitationContext';
// (no placeholder imports)

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
  is_tools_message?: boolean;
  content_length?: number;
  content_preserved?: boolean;
  post_tool_text?: string;
  role?: string;
  analysis_blocks?: any[];
  result?: any; // Tool completion result
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
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  
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
  const [toolsInProgress, setToolsInProgress] = useState<Map<string, string>>(new Map()); // Map of toolId -> toolName
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
  const processedCompletionMessageIdsRef = useRef<Set<string>>(new Set());
  const pendingFetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const fetchCancellationRef = useRef<{ current: boolean } | null>(null);

  const streamingTextRef = useRef('');
  const frozenInitialTextRef = useRef('');
  // No placeholder citation buffering

  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    switch (event.type) {
      case 'message_start':
        const newMessageId = event.message_id;
        
        if (activeMessageId) {
          console.log(`⚠️ Ignoring message_start - already have active message: ${activeMessageId}`);
          return;
        }
        
        // Do not cancel any pending backend citation fetch for the previous message.
        // We want the initial assistant message to still receive its citations
        // even if a tools or post-visualization message starts streaming now.
        
        if (newMessageId) {
          // Allow a new lifecycle for this message id.
          processedCompletionMessageIdsRef.current.delete(newMessageId);
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
        // Citations will be fetched from backend after message complete
        setCurrentBlockIndex(0);
        break;

      case 'new_message_start':
        // Handle new message for tools/visualization content
        if (event.is_tools_message && onMessageUpdate) {
          const toolsMessage: Message = {
            id: event.message_id || `tools-${Date.now()}`,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: (event.role as 'assistant' | 'user' | 'system') || 'assistant',
            content: '',  // Tools message has no text content, only analysis blocks
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],
            content_blocks: null,
            analysis_blocks: []  // Will be populated by tool events
          };
          
          // Add the new message to the chat
          onMessageUpdate(toolsMessage);
          
          // Keep the message phase as 'tools' since this is for visualizations
          setActiveMessageId(event.message_id || null);
          // Don't change phase - we're still in tools phase
        }
        // Handle new message for post-visualization content
        else if (event.is_post_visualization && onMessageUpdate) {
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
        // No placeholders: do not buffer; rely on backend fetch after completion
        console.log('Received citations_delta event');
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
        
        if (event.tool_id && event.tool_name) {
          setToolsInProgress(prev => {
            const newMap = new Map(prev);
            newMap.set(event.tool_id!, event.tool_name!);
            console.log(`Tool started: ${event.tool_name} (${event.tool_id})`);
            return newMap;
          });
        }
        break;

      case 'tool_complete':
        // Remove completed tool from in-progress set
        if (event.tool_id) {
          setToolsInProgress(prev => {
            const newMap = new Map(prev);
            const toolName = newMap.get(event.tool_id!) || 'unknown';
            newMap.delete(event.tool_id!);
            console.log(`Tool completed: ${toolName} (${event.tool_id}), remaining in progress: ${newMap.size}`);
            return newMap;
          });
        }
        
        // Process visualization data if present
        if (event.result && onVisualizationReady) {
          const toolName = event.tool_name;
          const toolData = event.result;
          
          if (toolName === 'generate_graph_data') {
            onVisualizationReady('chart', toolData, 0);
          } else if (toolName === 'generate_table_data') {
            onVisualizationReady('table', toolData, 0);
          } else if (toolName === 'generate_financial_metric') {
            onVisualizationReady('metric', toolData, 0);
          }
        }
        break;

      case 'message_complete':
        console.log('Message complete - processing citations');

        const completionMessageId = event.message_id || streamingMessageId || null;
        if (
          completionMessageId &&
          processedCompletionMessageIdsRef.current.has(completionMessageId)
        ) {
          console.log(
            `[useStreaming] Skipping duplicate message_complete for ${completionMessageId}`
          );
          return;
        }
        if (completionMessageId) {
          processedCompletionMessageIdsRef.current.add(completionMessageId);
          // Keep this bounded during long sessions.
          if (processedCompletionMessageIdsRef.current.size > 200) {
            const first = processedCompletionMessageIdsRef.current.values().next()
              .value as string | undefined;
            if (first) {
              processedCompletionMessageIdsRef.current.delete(first);
            }
          }
        }
        
        // Check if this is a tools message completion
        if (event.is_tools_message) {
          // For tools messages, update with analysis blocks if provided
          if (onMessageUpdate && event.message_id && event.analysis_blocks) {
            onMessageUpdate({
              id: event.message_id,
              sessionId: conversationId,
              timestamp: new Date().toISOString(),
              role: 'assistant',
              content: '',  // Tools message has no text content
              referencedDocuments: [],
              referencedAnalyses: [],
              citations: [],
              content_blocks: null,
              analysis_blocks: event.analysis_blocks || []
            });
          }
          setActiveMessageId(null);
          lastCompletedMessageIdRef.current = event.message_id || null;
          return;
        }
        
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
          
          // Citation markers will be included in the streamed content from backend
          
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
            id: (event.message_id || streamingMessageId)!,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: 'assistant',
            content: finalContent,
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],  // Attach real citations only after backend fetch
            content_blocks: event.content_blocks || [],
            analysis_blocks: event.analysis_blocks || []  // Get from streaming event if available
          };
          
          // First, send the streamed message immediately
          onMessageUpdate(message);
          
          // Store the message ID and current state for the async fetch
          // This ensures we're updating the correct message even if streaming restarts
          const messageIdToUpdate = (event.message_id || streamingMessageId)!;
          const originalContent = finalContent;
          const messageTimestamp = message.timestamp;
          const hadTools = toolsStarted;
          
          // Create a cancellation token to prevent stale updates
          const fetchCancelled = { current: false };
          fetchCancellationRef.current = fetchCancelled;
          
          // Then, fetch additional data (analysis blocks and citations) from backend
          // We'll batch these updates to avoid multiple onMessageUpdate calls
          
          const expectedCitationCount = (() => {
            const markerMatches = Array.from((originalContent || '').matchAll(/\[(\d+)\]/g));
            if (markerMatches.length === 0) return 0;
            return markerMatches.reduce((max, match) => {
              const marker = Number(match[1] || 0);
              return Number.isFinite(marker) ? Math.max(max, marker) : max;
            }, 0);
          })();

          const fetchAnalysisBlocksAndCitations = async () => {
            try {
              // Check if this fetch was cancelled (new message started streaming)
              if (fetchCancelled.current) {
                console.log('Fetch cancelled - new message started streaming');
                return;
              }
              
              // Import the API modules
              const { conversationsApi } = await import('@/lib/api/conversations');
              const { documentsApi } = await import('@/lib/api/documents');
              
              const normalize = (s: string) => (s || '').replace(/\s+/g, ' ').trim();
              const tryFetchBackendMessage = async (): Promise<import('@/types').Message | undefined> => {
                const messages = await conversationsApi.getConversationHistory(conversationId, 10);
                let backendMessage = messages.find(msg => msg.id === messageIdToUpdate);
                if (!backendMessage) {
                  backendMessage = messages.find(msg => msg.role === 'assistant' && normalize(msg.content) === normalize(originalContent));
                }
                if (!backendMessage) {
                  for (let i = messages.length - 1; i >= 0; i--) {
                    const m = messages[i];
                    if (m.role === 'assistant' && Array.isArray(m.citations) && m.citations.length > 0) {
                      backendMessage = m;
                      break;
                    }
                  }
                }
                return backendMessage;
              };
              
              const citationCount = (msg?: Message): number =>
                Array.isArray(msg?.citations) ? msg.citations.length : 0;

              const hasEnoughCitations = (msg?: Message): boolean => {
                const count = citationCount(msg);
                if (expectedCitationCount > 0) {
                  return count >= expectedCitationCount;
                }
                // If there are no citation markers in the message, there's nothing to poll for.
                return true;
              };

              // Poll only when citations are expected from visible [n] markers.
              let backendMessage = await tryFetchBackendMessage();
              let attempts = 0;
              const maxAttempts = 20;
              const delayMs = 1000;
              while (
                expectedCitationCount > 0 &&
                !fetchCancelled.current &&
                attempts < maxAttempts &&
                (!backendMessage || !hasEnoughCitations(backendMessage))
              ) {
                attempts++;
                await new Promise(res => setTimeout(res, delayMs));
                backendMessage = await tryFetchBackendMessage();
              }

              if (
                backendMessage &&
                expectedCitationCount > 0 &&
                citationCount(backendMessage) > 0 &&
                citationCount(backendMessage) < expectedCitationCount
              ) {
                console.warn(
                  `[useStreaming] Citation polling ended with partial citations: got ${citationCount(backendMessage)}/${expectedCitationCount} markers for message ${messageIdToUpdate}`
                );
              }
               
              if (!backendMessage) {
                console.log(`Message ${messageIdToUpdate} not found in backend`);
                return;
              }
              
              // Proceed to update the specific message even if newer messages completed
              // We guard only by fetch cancellation token to avoid stale writes
              if (fetchCancelled.current) {
                console.log(`Fetch cancelled for message ${messageIdToUpdate}`);
                return;
              }
              
              let needsUpdate = false;
              let updatedMessage: Message = {
                id: messageIdToUpdate,
                sessionId: conversationId,
                timestamp: messageTimestamp, // Preserve original timestamp
                role: 'assistant',
                content: originalContent, // Preserve exact original content
                referencedDocuments: [],
                referencedAnalyses: [],
                citations: [],
                content_blocks: message.content_blocks || [],
                analysis_blocks: message.analysis_blocks || []
              };
              
              // Check for analysis blocks
              if (hadTools && backendMessage.analysis_blocks && backendMessage.analysis_blocks.length > 0) {
                console.log(`Found ${backendMessage.analysis_blocks.length} analysis blocks from backend`);
                updatedMessage.analysis_blocks = backendMessage.analysis_blocks;
                needsUpdate = true;
              }
              
              // Check for citations
              if (backendMessage.citations && backendMessage.citations.length > 0) {
                console.log(`Found ${backendMessage.citations.length} citations from backend`);
                
                // Preserve full ordered list on the message so [1], [2], ... map correctly
                const allCitations = backendMessage.citations;

                // Add only rect-backed citations to the global cache for immediate highlighting
                const citationsWithRects = allCitations.filter(c => c.rects && c.rects.length > 0);
                console.log('[useStreaming] Citations with rects (for cache):', citationsWithRects.map(c => ({ 
                  id: c.id, 
                  documentId: c.documentId,
                  rectCount: c.rects?.length || 0,
                  text: c.citedText?.substring(0, 50)
                })));
                addCitations(citationsWithRects);
                
                // Attach all citations to the message so markers become clickable immediately
                updatedMessage.citations = allCitations;
                needsUpdate = true;

                // If backend content includes injected [n] markers and our displayed content does not, prefer backend content
                const backendContent: string | undefined = (backendMessage as any).content;
                const backendHasMarkers = !!backendContent && /\[(\d+)\]/.test(backendContent);
                const currentHasMarkers = /\[(\d+)\]/.test(updatedMessage.content || '');
                if (backendContent && backendHasMarkers && !currentHasMarkers) {
                  updatedMessage.content = backendContent;
                  needsUpdate = true;
                }
              } else if (expectedCitationCount > 0) {
                // Fallback: poll document-level citations and then attach to the message
                try {
                  const docIds = Array.from(documentMap.values());
                  const fetchAllDocCitations = async (): Promise<Citation[]> => {
                    const acc: Citation[] = [];
                    for (const docId of docIds) {
                      const docCites = await documentsApi.getDocumentCitations(docId);
                      acc.push(...docCites);
                    }
                    return acc;
                  };

                  let allDocCitations: Citation[] = [];
                  let attempts = 0;
                  const maxAttempts = 12; // up to ~9s with 750ms delay
                  const delayMs = 750;
                  while (!fetchCancelled.current && attempts < maxAttempts) {
                    allDocCitations = await fetchAllDocCitations();
                    if (allDocCitations.length > 0) break;
                    attempts++;
                    await new Promise(res => setTimeout(res, delayMs));
                  }

                  if (fetchCancelled.current) {
                    console.log('Doc-level citations poll cancelled');
                    return;
                  }

                  // First try strict message_id filter
                  const targetMessageId = backendMessage?.id || messageIdToUpdate;
                  let messageCitations: Citation[] = allDocCitations.filter(c => c.messageId === targetMessageId);

                  // If none, try to map by content occurrence order
                  if ((!messageCitations || messageCitations.length === 0)) {
                    const s = streamingTextRef.current || '';
                    const f = frozenInitialTextRef.current || '';
                    const hasMarkers = (t: string) => /\[(\d+)\]/.test(t);
                    const content = hasMarkers(s) ? s : hasMarkers(f) ? f : (s.length >= f.length ? s : f) || originalContent;
                    const scored = allDocCitations.map(c => {
                      const needleA = (c.displayText || '').trim();
                      const needleB = (c.citedText || '').trim();
                      let idx = -1;
                      if (needleA && content.includes(needleA)) idx = content.indexOf(needleA);
                      else if (needleB && content.includes(needleB)) idx = content.indexOf(needleB);
                      if (idx < 0 && c.searchableText && c.searchableText.length >= 2) {
                        const n = c.searchableText.trim();
                        if (n && content.includes(n)) idx = content.indexOf(n);
                      }
                      return { c, idx };
                    }).filter(x => x.idx >= 0);

                    if (scored.length > 0) {
                      scored.sort((a, b) => a.idx - b.idx);
                      const markerCount = (content.match(/\[(\d+)\]/g) || []).length;
                      messageCitations = scored.slice(0, Math.max(markerCount, 1)).map(x => x.c);
                    }
                  }

                  if (messageCitations && messageCitations.length > 0) {
                    console.log(`[useStreaming] Fallback mapped ${messageCitations.length} citations from document-level to message content (after polling)`);
                    const citationsWithRects = messageCitations.filter(c => c.rects && c.rects.length > 0);
                    addCitations(citationsWithRects);
                    updatedMessage.citations = messageCitations;
                    needsUpdate = true;
                  } else {
                    // As a last resort, attach the first N rect-backed citations to match marker count
                    const markerCount = (originalContent.match(/\[(\d+)\]/g) || []).length;
                    const rectBacked = allDocCitations.filter(c => c.rects && c.rects.length > 0);
                    if (markerCount > 0 && rectBacked.length > 0) {
                      const pick = rectBacked.slice(0, markerCount);
                      console.log(`[useStreaming] Last-resort attaching ${pick.length}/${markerCount} rect-backed doc citations to enable clickable markers (after polling)`);
                      addCitations(pick);
                      updatedMessage.citations = pick;
                      needsUpdate = true;
                    } else {
                      console.log('[useStreaming] No citations found in history or doc-level polling fallback');
                    }
                  }
                } catch (e) {
                  console.warn('Fallback document citations/content mapping failed:', e);
                }
              } else {
                console.log('[useStreaming] No citation markers in message; skipping citation fallback polling');
              }
              
              // Only call onMessageUpdate once if we have updates
              if (needsUpdate && !fetchCancelled.current) {
                console.log('[useStreamingChat] Updating message with backend data:', {
                  messageId: messageIdToUpdate,
                  hasAnalysisBlocks: !!updatedMessage.analysis_blocks?.length,
                  hasCitations: !!updatedMessage.citations?.length,
                  citationCount: updatedMessage.citations?.length || 0,
                  contentLength: updatedMessage.content.length,
                  contentPreview: updatedMessage.content.substring(0, 100)
                });
                onMessageUpdate(updatedMessage);
              }
            } catch (error) {
              console.error('Error fetching backend data:', error);
            }
          };
          
          // Only fetch backend data if we need it
          const shouldFetchBackendData = hadTools || expectedCitationCount > 0;
          if (shouldFetchBackendData) {
            // Clear any existing timeout
            if (pendingFetchTimeoutRef.current) {
              clearTimeout(pendingFetchTimeoutRef.current);
            }
            
            // Add a delay to ensure backend has finished processing
            pendingFetchTimeoutRef.current = setTimeout(() => {
              // Clear the timeout ref since we're executing
              pendingFetchTimeoutRef.current = null;
              fetchAnalysisBlocksAndCitations();
            }, 1500);
          } else {
            console.log('[useStreaming] Skipping backend poll: no tools and no citation markers');
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
      streamingMessageId, postToolMessageId, conversationId, onMessageUpdate, 
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
      
      // Clear any pending fetch
      if (pendingFetchTimeoutRef.current) {
        clearTimeout(pendingFetchTimeoutRef.current);
        pendingFetchTimeoutRef.current = null;
      }
      if (fetchCancellationRef.current) {
        fetchCancellationRef.current.current = true;
        fetchCancellationRef.current = null;
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
    toolsInProgress: Array.from(toolsInProgress.entries()).map(([id, name]) => ({ id, name })),
    completedVisualizations,
    
    // Citations (will be fetched from backend after message complete)
    streamingCitations: [],
    
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
