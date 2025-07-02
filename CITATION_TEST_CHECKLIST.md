# Citation Testing Checklist

## Pre-Test Setup
- [ ] Ensure backend server is running with latest changes
- [ ] Ensure frontend is running with latest changes
- [ ] Have a financial PDF ready to upload (preferably with tables, numbers, specific data)

## Test Steps

### 1. Upload Document
- [ ] Navigate to workspace
- [ ] Upload a financial PDF document
- [ ] Verify document appears in the viewer
- [ ] Note the document ID in browser console

### 2. Enable Browser Console Logging
- [ ] Open browser developer tools (F12)
- [ ] Go to Console tab
- [ ] Clear console
- [ ] Keep console open during testing

### 3. Ask Citation-Triggering Questions
Try these types of questions that should trigger citations:

- [ ] "What is the total revenue mentioned in this document?"
- [ ] "What are the specific financial metrics for Q3 2023?"
- [ ] "Can you list the key performance indicators with their exact values?"
- [ ] "What does the document say about operating expenses?"

### 4. Monitor Console During Streaming
Look for these console messages:

- [ ] `🚀 Starting new message: [message_id]`
- [ ] `Event: citations_delta`
- [ ] `Citation received: page_location - '[cited text]...'`
- [ ] `Adding citation to pending: [citation details]`
- [ ] `Processing [X] pending citations for message`

### 5. Verify Citation Display
After response completes:

- [ ] Check if citations appear as [1], [2], etc. in the response
- [ ] Hover over citations to see tooltips
- [ ] Click on a citation

### 6. Verify PDF Navigation
When clicking a citation:

- [ ] Document tab should activate
- [ ] PDF should scroll to the cited location
- [ ] Cited text should be highlighted

### 7. Backend Log Verification
Check backend logs for:

- [ ] `Found citation in streaming response: [type] - '[text]...'`
- [ ] `Storing [X] citations for message [id]`
- [ ] `Created citation [id] for document [doc_id]`

## Common Issues and Solutions

### No Citations Appearing
1. **Check document has file_id**:
   - In console: Look for document data with `claude_file_id`
   
2. **Verify streaming hook**:
   - Should see `useStreamingChatWithCitations` in console logs
   
3. **Check event types**:
   - Look for `citations_delta` events, not `citation`

### Citations Not Clickable
1. **Check MessageRenderer**:
   - Verify citation detection regex is working
   - Check if onCitationClick handler is passed

### PDF Not Highlighting
1. **Check CitationContext**:
   - Verify citations are stored in context
   - Check highlight creation in PDF viewer

## Success Criteria
- [ ] Citations appear as numbered references [1], [2] in chat responses
- [ ] Citations are clickable
- [ ] Clicking citation navigates to correct PDF location
- [ ] Cited text is highlighted in yellow
- [ ] Multiple citations work correctly
- [ ] Citations persist after page refresh