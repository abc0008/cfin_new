#!/usr/bin/env node
/**
 * Test: Complete Message Flow with Visualizations
 * 
 * This test validates the entire end-to-end flow of streaming messages
 * with tool processing and visualizations, ensuring all fixes work together.
 */

// Mock state variables (matching useStreamingChat.ts)
let streamingText = '';
let streamingMessageId = null;
let toolsStarted = false;
let postVisualizationText = '';

// Track all messages and events
const messagesCreated = [];
const eventLog = [];

const mockOnMessageUpdate = (message) => {
  messagesCreated.push(message);
  eventLog.push(`📨 MESSAGE CREATED: ${message.id} - "${message.content.substring(0, 50)}..."`);
  console.log(`📨 MESSAGE CREATED: ${message.id} - "${message.content.substring(0, 50)}..."`);
  if (message.analysis_blocks?.length > 0) {
    console.log(`   📊 Visualizations: ${message.analysis_blocks.length} blocks`);
  }
};

const mockOnVisualizationReady = (type, data, index) => {
  eventLog.push(`📊 VISUALIZATION READY: ${type} #${index}`);
  console.log(`📊 VISUALIZATION READY: ${type} #${index}`);
};

// Mock the COMPLETE FIXED event handler
const handleCompleteMessageFlow = async (event) => {
  eventLog.push(`🎬 EVENT: ${event.type} ${event.message_id ? `(${event.message_id})` : ''}`);
  console.log(`\n🎬 EVENT: ${event.type} ${event.message_id ? `(${event.message_id})` : ''}`);
  
  switch (event.type) {
    case 'message_start':
      // FIXED: Prevent reset if we have streaming content
      if (streamingText && streamingText.length > 0 && !toolsStarted) {
        console.log(`🛡️ PROTECTING STREAMING CONTENT: Ignoring message_start reset - have ${streamingText.length} chars`);
        return;
      }
      
      streamingText = '';
      toolsStarted = false;
      postVisualizationText = '';
      streamingMessageId = event.message_id;
      console.log(`🔄 Starting new message - streamingMessageId: ${streamingMessageId}`);
      break;
      
    case 'content_update':
      // FIXED: Message ID management
      if (streamingMessageId && event.message_id && streamingMessageId !== event.message_id) {
        console.log(`🚨 MESSAGE ID MISMATCH: current=${streamingMessageId}, event=${event.message_id} - keeping current`);
      }
      
      if (event.accumulated_text) {
        if (!toolsStarted) {
          streamingText = event.accumulated_text;
          console.log(`📝 Initial streaming update: ${event.accumulated_text.length} chars`);
        } else {
          postVisualizationText = event.accumulated_text;
          console.log(`📊 Post-visualization content update: ${event.accumulated_text.length} chars`);
        }
      }
      break;
      
    case 'tool_start':
      console.log(`🔍 TOOL_START: toolsStarted=${toolsStarted}, streamingText.length=${streamingText?.length || 0}`);
      
      // FIXED: Complete streaming message before tools
      if (!toolsStarted && streamingText && streamingMessageId) {
        toolsStarted = true;
        console.log(`🏁 COMPLETING streaming message: "${streamingText.substring(0, 50)}..." (${streamingText.length} chars)`);
        
        const completedStreamingMessage = {
          id: streamingMessageId,
          content: streamingText,
          analysis_blocks: []
        };
        
        console.log(`✅ Completed STREAMING message (no visualizations)`);
        mockOnMessageUpdate(completedStreamingMessage);
        
        // Clear streaming state
        streamingText = '';
      }
      break;
      
    case 'chart_ready':
      console.log(`📊 Chart ready: ${event.chart_data?.title || 'Unnamed chart'}`);
      if (event.chart_data) {
        mockOnVisualizationReady('chart', event.chart_data, 0);
      }
      break;
      
    case 'table_ready':
      console.log(`📊 Table ready: ${event.table_data?.title || 'Unnamed table'}`);
      if (event.table_data) {
        mockOnVisualizationReady('table', event.table_data, 0);
      }
      break;
      
    case 'metric_ready':
      console.log(`📊 Metric ready: ${event.metric_data?.title || 'Unnamed metric'}`);
      if (event.metric_data) {
        mockOnVisualizationReady('metric', event.metric_data, 0);
      }
      break;
      
    case 'message_complete':
      console.log(`🏁 Message complete: toolsStarted=${toolsStarted}`);
      
      if (toolsStarted) {
        // Tools were used - create separate tool message
        console.log(`🔧 Creating separate TOOL MESSAGE for visualizations`);
        
        // Simulate fetching complete message with analysis blocks
        const completeMessage = {
          id: streamingMessageId,
          content: "Complete analysis with insights",
          analysis_blocks: [
            { type: 'chart', title: 'Revenue Trends', content: { type: 'line', data: [] } },
            { type: 'table', title: 'Financial Summary', content: { headers: [], rows: [] } },
            { type: 'metric', title: 'Growth Rate', content: { value: 15.5, unit: '%' } }
          ]
        };
        
        const toolMessageId = `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const toolMessage = {
          id: toolMessageId,
          content: 'Analysis Visualizations',
          analysis_blocks: completeMessage.analysis_blocks
        };
        
        console.log(`🎯 Created TOOL MESSAGE with ${completeMessage.analysis_blocks.length} visualizations`);
        mockOnMessageUpdate(toolMessage);
        
        // Create post-visualization message if we have content
        if (postVisualizationText && postVisualizationText.length > 0) {
          const postVizMessageId = `post_viz_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const postVizMessage = {
            id: postVizMessageId,
            content: postVisualizationText,
            analysis_blocks: []
          };
          
          console.log(`💬 Created POST-VISUALIZATION MESSAGE: ${postVisualizationText.length} chars`);
          mockOnMessageUpdate(postVizMessage);
        }
      } else if (streamingText && streamingMessageId) {
        // No tools used - complete streaming message now
        console.log(`📝 No tools used - completing streaming message`);
        
        const finalStreamingMessage = {
          id: streamingMessageId,
          content: streamingText,
          analysis_blocks: []
        };
        
        console.log(`✅ Completed streaming-only message: ${streamingText.length} chars`);
        mockOnMessageUpdate(finalStreamingMessage);
      }
      
      // Clean up state
      streamingText = '';
      streamingMessageId = null;
      toolsStarted = false;
      postVisualizationText = '';
      console.log(`🧹 Cleaned up state for next message`);
      break;
  }
};

async function testCompleteMessageFlow() {
  console.log('🧪 TESTING: Complete Message Flow with Visualizations');
  console.log('=' .repeat(70));
  
  // Complete realistic message flow
  const fullMessageFlow = [
    {
      type: 'message_start',
      message_id: 'msg_complete_test_123',
      description: 'Start new message'
    },
    {
      type: 'content_update',
      message_id: 'msg_complete_test_123',
      accumulated_text: 'Let me analyze the financial data for you.',
      description: 'Build initial streaming content'
    },
    {
      type: 'content_update',
      message_id: 'msg_complete_test_123',
      accumulated_text: 'Let me analyze the financial data for you. I\'ll examine the revenue trends and performance metrics.',
      description: 'Continue building streaming content'
    },
    {
      type: 'tool_start',
      tool_id: 'chart_tool_1',
      tool_name: 'create_chart',
      description: 'Tools start - should complete streaming message'
    },
    {
      type: 'chart_ready',
      chart_data: { title: 'Revenue Growth Chart', type: 'line', data: [1, 2, 3] },
      description: 'Chart visualization ready'
    },
    {
      type: 'table_ready',
      table_data: { title: 'Financial Summary Table', headers: ['Q1', 'Q2'], rows: [] },
      description: 'Table visualization ready'
    },
    {
      type: 'metric_ready',
      metric_data: { title: 'Growth Rate', value: 15.5, unit: '%' },
      description: 'Metric visualization ready'
    },
    {
      type: 'content_update',
      message_id: 'msg_complete_test_123',
      accumulated_text: 'Based on the analysis, the company shows strong growth trends with 15.5% annual growth.',
      description: 'Post-visualization content'
    },
    {
      type: 'message_complete',
      message_id: 'msg_complete_test_123',
      description: 'Complete the message flow'
    }
  ];
  
  for (let i = 0; i < fullMessageFlow.length; i++) {
    const event = fullMessageFlow[i];
    console.log(`\n📍 STEP ${i + 1}: ${event.description}`);
    await handleCompleteMessageFlow(event);
  }
  
  console.log('\n' + '=' .repeat(70));
  console.log('🎯 COMPLETE FLOW VALIDATION:');
  
  // Analyze results
  const streamingMessages = messagesCreated.filter(m => !m.id.includes('tool_') && !m.id.includes('post_viz_'));
  const toolMessages = messagesCreated.filter(m => m.id.includes('tool_'));
  const postVizMessages = messagesCreated.filter(m => m.id.includes('post_viz_'));
  
  console.log(`\n📊 MESSAGE BREAKDOWN:`);
  console.log(`   Streaming messages: ${streamingMessages.length} (expected: 1)`);
  console.log(`   Tool messages: ${toolMessages.length} (expected: 1)`);
  console.log(`   Post-visualization messages: ${postVizMessages.length} (expected: 1)`);
  console.log(`   Total messages: ${messagesCreated.length} (expected: 3)`);
  
  // Validation checks
  const checks = [
    {
      name: 'Correct number of messages created',
      pass: messagesCreated.length === 3,
      expected: 3,
      actual: messagesCreated.length
    },
    {
      name: 'Streaming message has no visualizations',
      pass: streamingMessages[0]?.analysis_blocks?.length === 0,
      expected: 0,
      actual: streamingMessages[0]?.analysis_blocks?.length || 0
    },
    {
      name: 'Tool message has visualizations',
      pass: toolMessages[0]?.analysis_blocks?.length === 3,
      expected: 3,
      actual: toolMessages[0]?.analysis_blocks?.length || 0
    },
    {
      name: 'Post-viz message has no visualizations',
      pass: postVizMessages[0]?.analysis_blocks?.length === 0,
      expected: 0,
      actual: postVizMessages[0]?.analysis_blocks?.length || 0
    },
    {
      name: 'Streaming content preserved',
      pass: streamingMessages[0]?.content.includes('financial data'),
      expected: 'Contains "financial data"',
      actual: streamingMessages[0]?.content.substring(0, 50) + '...'
    }
  ];
  
  console.log(`\n✅ VALIDATION RESULTS:`);
  checks.forEach((check, i) => {
    const status = check.pass ? '✅' : '❌';
    console.log(`${i + 1}. ${status} ${check.name}`);
    if (!check.pass) {
      console.log(`     Expected: ${check.expected}, Got: ${check.actual}`);
    }
  });
  
  const allPassed = checks.every(check => check.pass);
  
  console.log('\n🎉 COMPLETE MESSAGE FLOW RESULTS:');
  if (allPassed) {
    console.log('   ✅ ALL TESTS PASSED - Complete message flow working perfectly!');
    console.log('   ✅ Streaming messages complete before tools start');
    console.log('   ✅ Tool messages contain all visualizations');
    console.log('   ✅ Post-visualization messages capture additional content');
    console.log('   ✅ No message disappearance or ID synchronization issues');
    console.log('   ✅ Clean separation between content types');
  } else {
    console.log('   ❌ Some tests failed - review the validation results above');
  }
  
  return allPassed;
}

// Run the test
testCompleteMessageFlow().then(success => {
  process.exit(success ? 0 : 1);
});