// Timezone Verification Test
// Run this in your browser console to verify timezone handling

console.log('=== Timezone Verification Test ===');
console.log('Your timezone:', Intl.DateTimeFormat().resolvedOptions().timeZone);
console.log('Timezone offset (minutes from UTC):', new Date().getTimezoneOffset());

// Test UTC timestamp like those from backend
const backendTimestamp = "2025-06-19T05:40:52.476003";
console.log('\n--- Backend Timestamp Test ---');
console.log('Raw UTC timestamp:', backendTimestamp);
console.log('Parsed as Date:', new Date(backendTimestamp));
console.log('Local time display:', new Date(backendTimestamp).toLocaleTimeString());
console.log('UTC time display:', new Date(backendTimestamp).toUTCString());

// Test frontend timestamp creation
console.log('\n--- Frontend Timestamp Creation ---');
const now = new Date();
console.log('Current local time:', now.toLocaleTimeString());
console.log('ISO string (UTC):', now.toISOString());
console.log('ISO parsed back to local:', new Date(now.toISOString()).toLocaleTimeString());

// Simulate the issue
console.log('\n--- Simulating the Issue ---');
const userMessageTime = new Date('2025-06-19T05:38:00Z'); // 12:38 AM Chicago time
const assistantMessageTime = new Date('2025-06-19T05:40:00Z'); // Should be 12:40 AM Chicago time

console.log('User message UTC:', userMessageTime.toISOString());
console.log('User message local:', userMessageTime.toLocaleTimeString());
console.log('Assistant message UTC:', assistantMessageTime.toISOString());
console.log('Assistant message local:', assistantMessageTime.toLocaleTimeString());

// Test the formatTimestamp function
function formatTimestamp(timestamp) {
  try {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    if (isNaN(date.getTime())) {
      return 'Invalid time';
    }
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  } catch (error) {
    return 'Invalid time';
  }
}

console.log('\n--- formatTimestamp Function Test ---');
console.log('Format user time:', formatTimestamp(userMessageTime));
console.log('Format assistant time:', formatTimestamp(assistantMessageTime));
console.log('Format backend timestamp:', formatTimestamp(backendTimestamp));

// Check if times are showing correctly
const timeDiff = assistantMessageTime.getTime() - userMessageTime.getTime();
console.log('\n--- Time Difference Check ---');
console.log('Time difference (ms):', timeDiff);
console.log('Time difference (minutes):', timeDiff / 1000 / 60);
console.log('Expected: 2 minutes');

console.log('\n=== End of Test ===');