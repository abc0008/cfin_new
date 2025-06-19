// Debug script to understand the timestamp issue
console.log('=== Timezone Debug ===');
console.log('Current timezone:', Intl.DateTimeFormat().resolvedOptions().timeZone);
console.log('Timezone offset (minutes from UTC):', new Date().getTimezoneOffset());

// Test the timestamps from the chat logs
const userTimestamp = "2025-06-19T06:10:19.280Z";  // Document upload
const assistantTimestamp = "2025-06-19T06:13:25.152831";  // Assistant response

console.log('\n--- Raw Timestamps ---');
console.log('User timestamp:', userTimestamp);
console.log('Assistant timestamp:', assistantTimestamp);

// Parse both timestamps
const userDate = new Date(userTimestamp);
const assistantDate = new Date(assistantTimestamp);

console.log('\n--- Parsed Dates ---');
console.log('User date object:', userDate);
console.log('Assistant date object:', assistantDate);

console.log('\n--- UTC Display ---');
console.log('User UTC:', userDate.toUTCString());
console.log('Assistant UTC:', assistantDate.toUTCString());

console.log('\n--- Local Display ---');
console.log('User local:', userDate.toLocaleTimeString());
console.log('Assistant local:', assistantDate.toLocaleTimeString());

console.log('\n--- formatTimestamp Function Test ---');
function formatTimestamp(timestamp, options = { hour: '2-digit', minute: '2-digit', hour12: true }) {
  try {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    if (isNaN(date.getTime())) {
      return 'Invalid time';
    }
    return date.toLocaleTimeString([], options);
  } catch (error) {
    return 'Invalid time';
  }
}

console.log('User formatted:', formatTimestamp(userTimestamp));
console.log('Assistant formatted:', formatTimestamp(assistantTimestamp));

// Check the actual time difference
const timeDiff = assistantDate.getTime() - userDate.getTime();
console.log('\n--- Time Difference ---');
console.log('Difference (ms):', timeDiff);
console.log('Difference (minutes):', timeDiff / 1000 / 60);
console.log('Expected: ~3 minutes');

// Check if there's any issue with the assistant timestamp format
console.log('\n--- Assistant Timestamp Analysis ---');
console.log('Assistant timestamp ends with Z?', assistantTimestamp.endsWith('Z'));
console.log('Assistant timestamp has timezone?', assistantTimestamp.includes('+') || assistantTimestamp.includes('Z'));

// Try adding Z to assistant timestamp
const assistantWithZ = assistantTimestamp + (assistantTimestamp.endsWith('Z') ? '' : 'Z');
const assistantDateWithZ = new Date(assistantWithZ);
console.log('Assistant with Z:', assistantWithZ);
console.log('Assistant with Z parsed:', assistantDateWithZ);
console.log('Assistant with Z local:', assistantDateWithZ.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true }));