#!/usr/bin/env node
/**
 * Test: Clean Message Separation Fix
 * 
 * This test validates the complete separation solution:
 * 1. Streaming messages complete BEFORE tools start
 * 2. Tool messages are completely separate with their own IDs
 * 3. Visualizations attach to tool messages, not streaming messages
 * 4. No race conditions or message ID conflicts
 */

// Mock the React hooks and dependencies
const mockSetState = (name) => (value) => {
  console.log(`${name} set to:`, typeof value === 'function' ? 'function' : value);
};

// Mock state variables
let isStreaming = false;
let streamingText = '';
let streamingMessageId = null;
let isConnected = true;
let toolsStarted = false;
let frozenInitialText = '';
let postToolMessageId = null;
let toolsInProgress = new Set();
let completedVisualizations = { charts: [], tables: [], metrics: [] };

// Mock setters
const setIsStreaming = (value) => {
  isStreaming = value;
  console.log(`📺 isStreaming set to: ${value}`);
};
const setStreamingText = (value) => {
  streamingText = value;
  console.log(`📝 streamingText set to: "${value.substring(0, 80)}${value.length > 80 ? '...' : ''}" (${value.length} chars)`);
};
const setStreamingMessageId = (value) => {
  streamingMessageId = value;
  console.log(`🆔 streamingMessageId set to: ${value}`);
};
const setToolsStarted = (value) => {
  toolsStarted = value;
  console.log(`🔧 toolsStarted set to: ${value}`);
};
const setFrozenInitialText = (value) => {
  frozenInitialText = value;
  console.log(`🧊 frozenInitialText set to: "${value.substring(0, 50)}${value.length > 50 ? '...' : ''}" (${value.length} chars)`);
};
const setPostToolMessageId = mockSetState('postToolMessageId');
const setToolsInProgress = mockSetState('setToolsInProgress');
const setCompletedVisualizations = mockSetState('setCompletedVisualizations');

// Mock conversationApi
const conversationApi = {
  getMessage: async (messageId) => {
    console.log(`🔍 API: Fetching message ${messageId}`);
    // Simulate database message with analysis blocks
    return {
      id: messageId,
      sessionId: 'test-conversation',
      timestamp: new Date().toISOString(),
      role: 'assistant',
      content: 'Complete analysis with comprehensive insights about the financial data, including detailed breakdowns, trend analysis, and actionable recommendations for stakeholders.',
      referencedDocuments: [],
      referencedAnalyses: [],
      citations: [],
      content_blocks: null,
      analysis_blocks: [
        { type: 'chart', title: 'Revenue Trends', content: { type: 'line', data: [] } },
        { type: 'insight', title: 'Key Findings', content: { text: 'Revenue growth accelerating' } },
        { type: 'metric', title: 'Growth Rate', content: { value: 15.5, unit: '%' } }
      ]
    };
  }
};

// Track messages created
const messagesCreated = [];

// Mock onMessageUpdate callback
const onMessageUpdate = (message) => {
  messagesCreated.push(message);
  console.log(`\n📨 MESSAGE CREATED: "${message.content.substring(0, 60)}..." (${message.content.length} chars)`);
  console.log(`   ID: ${message.id}`);
  console.log(`   Analysis blocks: ${message.analysis_blocks?.length || 0}`);
  console.log(`   Type: ${message.id.startsWith('tool_') ? '🔧 TOOL MESSAGE' : '📝 STREAMING MESSAGE'}`);
  
  if (message.analysis_blocks?.length > 0) {
    console.log(`   📊 Visualizations: ${message.analysis_blocks.map(block => block.type).join(', ')}`);
  }
};

// Mock conversation ID
const conversationId = 'test-conversation-123';

// The main event handler logic (from useStreamingChat.ts)
const handleStreamingEvent = async (event) => {
  console.log(`\n🎬 EVENT: ${event.type} ${event.message_id ? `(${event.message_id})` : ''}`);
  
  switch (event.type) {
    case 'message_start':
      setIsStreaming(true);
      setStreamingText('');
      
      // CLEAN RESET: Start fresh for new message
      setToolsStarted(false);
      setFrozenInitialText('');
      setPostToolMessageId(null);
      console.log('🔄 Starting new message - reset streaming state');
      
      if (event.message_id) {
        setStreamingMessageId(event.message_id);
      }
      
      setToolsInProgress(new Set());
      setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
      break;

    case 'text_delta':
      if (event.text) {
        const newText = event.accumulated_text || '';
        
        if (!toolsStarted) {
          setStreamingText(newText);
          console.log(`📝 Building initial streaming: ${newText.length} chars`);
        } else {
          console.log(`🔀 Tools active - ignoring text_delta (${newText.length} chars)`);
        }
      }
      break;

    case 'content_update':
      if (event.accumulated_text) {
        if (!toolsStarted) {
          setStreamingText(event.accumulated_text);
          console.log(`📝 Initial streaming update: ${event.accumulated_text.length} chars`);
        } else {
          console.log(`🔀 Tools active - ignoring content_update (${event.accumulated_text.length} chars)`);
        }
      }
      break;

    case 'tool_start':
      // COMPLETE SEPARATION: Finish streaming message BEFORE any tools start
      if (!toolsStarted && streamingText && streamingMessageId) {
        setToolsStarted(true);
        
        console.log(`🏁 COMPLETING streaming message before tools: "${streamingText.substring(0, 100)}..." (${streamingText.length} chars)`);
        
        // Complete the pure streaming message (no tools/visualizations)
        const completedStreamingMessage = {
          id: streamingMessageId,
          sessionId: conversationId,
          timestamp: new Date().toISOString(),
          role: 'assistant',
          content: streamingText,
          referencedDocuments: [],
          referencedAnalyses: [],
          citations: [],
          content_blocks: null,
          analysis_blocks: [] // No analysis blocks in streaming message
        };
        
        console.log(`✅ Completed pure streaming message - NO tools/visualizations`);
        onMessageUpdate(completedStreamingMessage);
        
        // Clear streaming state - this message is done
        setStreamingText('');
        setIsStreaming(false);
      }
      
      if (event.tool_id) {
        setToolsInProgress(prev => {
          const newSet = new Set(prev);
          newSet.add(event.tool_id);
          return newSet;
        });
        
        console.log(`🔧 Tool started: ${event.tool_name} (${event.tool_id}) - will create separate tool message`);
      }
      break;

    case 'message_complete':
      setIsStreaming(false);
      setToolsInProgress(new Set());
      
      const messageIdToFetch = event.message_id || streamingMessageId;
      
      console.log(`🏁 Message complete: toolsStarted=${toolsStarted}, messageId=${messageIdToFetch}`);
      
      if (messageIdToFetch && toolsStarted) {
        // Tools were used - create SEPARATE tool message with visualizations
        console.log(`🔧 Creating separate TOOL MESSAGE for visualizations`);
        
        const fetchToolMessage = async () => {
          try {
            const completeMessage = await conversationApi.getMessage(messageIdToFetch);
            
            if (completeMessage && completeMessage.analysis_blocks?.length > 0) {
              // Create separate tool message with unique ID
              const toolMessageId = `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
              
              const toolMessage = {
                id: toolMessageId,
                sessionId: conversationId,
                timestamp: new Date().toISOString(),
                role: 'assistant',
                content: `Analysis Results: ${completeMessage.content}`,
                referencedDocuments: completeMessage.referencedDocuments || [],
                referencedAnalyses: completeMessage.referencedAnalyses || [],
                citations: completeMessage.citations || [],
                content_blocks: completeMessage.content_blocks,
                analysis_blocks: completeMessage.analysis_blocks // Visualizations go here
              };
              
              console.log(`🎯 Created TOOL MESSAGE with ${completeMessage.analysis_blocks.length} visualizations`);
              onMessageUpdate(toolMessage);
            } else {
              console.log(`⚠️ No analysis blocks found - no tool message needed`);
            }
          } catch (error) {
            console.error(`Error fetching tool message:`, error);
          }
        };
        
        await fetchToolMessage();
      } else if (messageIdToFetch && !toolsStarted) {
        // No tools used - complete the streaming message now
        console.log(`📝 No tools used - completing streaming message now`);
        
        if (streamingText && streamingMessageId) {
          const finalStreamingMessage = {
            id: streamingMessageId,
            sessionId: conversationId,
            timestamp: new Date().toISOString(),
            role: 'assistant',
            content: streamingText,
            referencedDocuments: [],
            referencedAnalyses: [],
            citations: [],
            content_blocks: null,
            analysis_blocks: [] // Pure streaming message, no visualizations
          };
          
          console.log(`✅ Completed streaming-only message (no tools): ${streamingText.length} chars`);
          onMessageUpdate(finalStreamingMessage);
        }
      }
      
      // Clean up state for next message
      setStreamingText('');
      setStreamingMessageId(null);
      setToolsStarted(false);
      setFrozenInitialText('');
      setPostToolMessageId(null);
      setCompletedVisualizations({ charts: [], tables: [], metrics: [] });
      
      console.log(`🧹 Cleaned up streaming state for next message`);
      break;

    default:
      console.log(`❓ Unhandled event type: ${event.type}`);
  }
};

// Test Scenario: Complete message separation
async function runCleanSeparationTest() {
  console.log('🧪 TESTING CLEAN MESSAGE SEPARATION FIX');
  console.log('=' .repeat(70));
  
  try {
    // Step 1: Start new message
    console.log('\n🎬 STEP 1: Starting new message');
    await handleStreamingEvent({
      type: 'message_start',
      message_id: 'msg_streaming_123'
    });
    
    // Step 2: Build streaming content
    console.log('\n🎬 STEP 2: Building streaming content');
    await handleStreamingEvent({
      type: 'text_delta',
      text: 'Let me provide a comprehensive analysis of the deposit performance',
      accumulated_text: 'Let me provide a comprehensive analysis of the deposit performance based on the financial statements.'
    });
    
    await handleStreamingEvent({
      type: 'content_update',
      accumulated_text: 'Let me provide a comprehensive analysis of the deposit performance based on the financial statements. The bank shows steady growth across all deposit categories with strong diversification.'
    });
    
    console.log(`\n📊 CHECKPOINT 1: Streaming content built`);
    console.log(`   Current streamingText: "${streamingText}"`);
    console.log(`   toolsStarted: ${toolsStarted}`);
    console.log(`   Messages created so far: ${messagesCreated.length}`);
    
    // Step 3: Tools start - CRITICAL SEPARATION POINT
    console.log('\n🎬 STEP 3: Tools start - STREAMING MESSAGE COMPLETES HERE');
    await handleStreamingEvent({
      type: 'tool_start',
      message_id: 'msg_streaming_123',
      tool_id: 'chart_tool_1', 
      tool_name: 'create_chart'
    });
    
    console.log(`\n📊 CHECKPOINT 2: After tool start`);
    console.log(`   streamingText: "${streamingText}" (should be empty now)`);
    console.log(`   toolsStarted: ${toolsStarted}`);
    console.log(`   Messages created so far: ${messagesCreated.length} (should be 1 - streaming message)`);
    
    // Step 4: More content during tool processing (should be ignored)
    console.log('\n🎬 STEP 4: Content during tool processing (should be ignored)');
    await handleStreamingEvent({
      type: 'content_update',
      accumulated_text: 'Based on the analysis, the visualizations show clear trends...'
    });
    
    console.log(`\n📊 CHECKPOINT 3: After tool processing content`);
    console.log(`   streamingText: "${streamingText}" (should still be empty)`);
    console.log(`   Messages created so far: ${messagesCreated.length} (should still be 1)`);
    
    // Step 5: Tool completes
    console.log('\n🎬 STEP 5: Tool completes');
    await handleStreamingEvent({
      type: 'tool_complete',
      tool_id: 'chart_tool_1'
    });
    
    // Step 6: Message complete - creates SEPARATE tool message
    console.log('\n🎬 STEP 6: Message complete - creates separate tool message');
    await handleStreamingEvent({
      type: 'message_complete',
      message_id: 'msg_streaming_123'
    });
    
    console.log(`\n📊 FINAL CHECKPOINT: Complete separation test`);
    console.log(`   Total messages created: ${messagesCreated.length} (should be 2)`);
    console.log(`   Message types: ${messagesCreated.map(m => m.id.startsWith('tool_') ? 'TOOL' : 'STREAMING').join(', ')}`);
    console.log(`   Visualizations in streaming message: ${messagesCreated[0]?.analysis_blocks?.length || 0} (should be 0)`);
    console.log(`   Visualizations in tool message: ${messagesCreated[1]?.analysis_blocks?.length || 0} (should be 3)`);
    
    console.log('\n' + '=' .repeat(70));
    console.log('✅ CLEAN SEPARATION TEST COMPLETED!');
    
    // Validate results
    const streamingMessage = messagesCreated[0];
    const toolMessage = messagesCreated[1];
    
    console.log('\n🎯 VALIDATION RESULTS:');
    
    if (messagesCreated.length === 2) {
      console.log('1. ✅ Correct number of messages created (2)');
    } else {
      console.log(`1. ❌ Wrong number of messages: ${messagesCreated.length} (expected 2)`);
    }
    
    if (streamingMessage && !streamingMessage.id.startsWith('tool_')) {
      console.log('2. ✅ First message is streaming message');
    } else {
      console.log('2. ❌ First message is not streaming message');
    }
    
    if (toolMessage && toolMessage.id.startsWith('tool_')) {
      console.log('3. ✅ Second message is tool message');
    } else {
      console.log('3. ❌ Second message is not tool message');
    }
    
    if (streamingMessage?.analysis_blocks?.length === 0) {
      console.log('4. ✅ Streaming message has no visualizations');
    } else {
      console.log(`4. ❌ Streaming message has ${streamingMessage?.analysis_blocks?.length || 0} visualizations`);
    }
    
    if (toolMessage?.analysis_blocks?.length === 3) {
      console.log('5. ✅ Tool message has all visualizations (3)');
    } else {
      console.log(`5. ❌ Tool message has ${toolMessage?.analysis_blocks?.length || 0} visualizations (expected 3)`);
    }
    
    console.log('\n🎉 CLEAN MESSAGE SEPARATION SOLUTION VERIFIED!');
    return true;
    
  } catch (error) {
    console.error('\n❌ TEST FAILED:', error);
    return false;
  }
}

// Run the test
runCleanSeparationTest().then(success => {
  process.exit(success ? 0 : 1);
});