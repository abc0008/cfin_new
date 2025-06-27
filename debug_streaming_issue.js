#!/usr/bin/env node
/**
 * Debug Test: Multiple message_start Events Issue
 * 
 * This test reproduces the exact sequence from StreamingExample8.md to verify
 * that multiple message_start events are resetting streaming state before tool_start
 */

// Simulate the exact sequence from StreamingExample8.md
const eventSequence = [
  {
    type: 'message_start',
    message_id: 'msg_123',
    event: '1st message_start'
  },
  {
    type: 'content_update',
    accumulated_text: 'Let me provide a comprehensive analysis of the deposit performance based on the financial statements.',
    event: 'Initial content'
  },
  {
    type: 'message_start', // This is the problem - 2nd message_start resets everything
    message_id: 'msg_456', 
    event: '2nd message_start - RESETS STATE'
  },
  {
    type: 'tool_start',
    tool_id: 'chart_tool',
    tool_name: 'create_chart',
    event: 'Tool start - but state was reset'
  }
];

// Mock state variables (matching useStreamingChat.ts)
let streamingText = '';
let streamingMessageId = null;
let toolsStarted = false;

// Track messages created
const messagesCreated = [];

const mockOnMessageUpdate = (message) => {
  messagesCreated.push(message);
  console.log(`📨 MESSAGE CREATED: ${message.id} - "${message.content.substring(0, 50)}..."`);
};

console.log('🚨 DEBUGGING: Multiple message_start Events Issue');
console.log('=' .repeat(60));

eventSequence.forEach((event, index) => {
  console.log(`\n📍 EVENT ${index + 1}: ${event.type} - ${event.event}`);
  
  switch (event.type) {
    case 'message_start':
      console.log(`   🔄 BEFORE: toolsStarted=${toolsStarted}, streamingText="${streamingText}", streamingMessageId=${streamingMessageId}`);
      
      // This is the problematic reset from useStreamingChat.ts lines 72-76
      toolsStarted = false;
      streamingText = '';
      streamingMessageId = event.message_id;
      
      console.log(`   🔄 AFTER RESET: toolsStarted=${toolsStarted}, streamingText="${streamingText}", streamingMessageId=${streamingMessageId}`);
      break;
      
    case 'content_update':
      streamingText = event.accumulated_text;
      console.log(`   📝 CONTENT SET: "${streamingText.substring(0, 50)}..." (${streamingText.length} chars)`);
      break;
      
    case 'tool_start':
      // This is the exact debug check I added to useStreamingChat.ts
      console.log(`   🔍 TOOL_START DEBUG: toolsStarted=${toolsStarted}, streamingText.length=${streamingText?.length || 0}, streamingMessageId=${streamingMessageId}`);
      console.log(`   🔍 STREAMING CONTENT: "${streamingText?.substring(0, 100)}..."`);
      
      // This is the conditional that's failing
      const conditionPassed = !toolsStarted && streamingText && streamingMessageId;
      console.log(`   🧪 CONDITION CHECK: (!toolsStarted && streamingText && streamingMessageId) = ${conditionPassed}`);
      
      if (conditionPassed) {
        console.log(`   ✅ CONDITION PASSED: Would complete streaming message`);
        const completedMessage = {
          id: streamingMessageId,
          content: streamingText,
          analysis_blocks: []
        };
        mockOnMessageUpdate(completedMessage);
        streamingText = '';
        toolsStarted = true;
      } else {
        console.log(`   ❌ CONDITION FAILED: Cannot complete streaming message`);
        console.log(`     - toolsStarted: ${toolsStarted} (should be false)`);
        console.log(`     - streamingText: "${streamingText}" (should have content)`);
        console.log(`     - streamingMessageId: ${streamingMessageId} (should exist)`);
      }
      break;
  }
});

console.log('\n' + '=' .repeat(60));
console.log('🎯 DIAGNOSIS RESULTS:');

if (messagesCreated.length === 0) {
  console.log('❌ CONFIRMED: Multiple message_start events reset streaming state');
  console.log('❌ The second message_start cleared streamingText before tool_start');
  console.log('❌ This is why the conditional check fails and streaming message disappears');
} else {
  console.log('✅ Streaming message was created successfully');
}

console.log('\n💡 ROOT CAUSE IDENTIFIED:');
console.log('   - First message_start sets up streaming state');
console.log('   - Content_update builds streaming text');
console.log('   - Second message_start RESETS streamingText to empty string');
console.log('   - Tool_start condition fails because streamingText is now empty');
console.log('   - No streaming message is created, content disappears');

console.log('\n🔧 FIX NEEDED:');
console.log('   - Prevent message_start from resetting state if streaming is in progress');
console.log('   - Or complete streaming message on first message_start reset attempt');
console.log('   - Or ignore subsequent message_start events during streaming');