# Plan: Feature for Suggesting Next 3 Most Likely Questions

This document outlines the plan to implement a feature that suggests the next three most likely questions a user might ask. These suggestions will be based on the current chat conversation history, the last assistant response, and a summary of the content displayed in the analysis pane.

## I. Backend Modifications (`/Users/alexcardell/AlexCoding_Local/cfin/backend`)

### 1. Modified API Endpoint for Suggested Questions

-   **Path:** `/api/v1/chat/suggest-questions`
-   **Method:** `POST`
-   **Request Body Schema:**
    ```json
    {
      "conversation_history": [
        { "role": "user", "content": "User's message..." },
        { "role": "assistant", "content": "Assistant's response..." }
      ],
      "last_assistant_response": "The latest response from the assistant.",
      "analysis_context_summary": "A concise text summary of the current, relevant content or findings displayed in the analysis pane.",
      "document_context_id": "Optional ID of relevant document"
    }
    ```
    *   **`analysis_context_summary`**: This field is key. It should contain a textual summary of what's currently shown or has been concluded in the analysis pane.
-   **Response Body Schema (Success - 200 OK):**
    ```json
    {
      "suggested_questions": [
        "First suggested question?",
        "Second suggested question?",
        "Third suggested question."
      ]
    }
    ```

### 2. New/Modified Service for Suggestion Logic (`services/suggestion_service.py`)

-   **Function (Example):**
    ```python
    async def get_suggested_questions(
        conversation_history: list,
        last_assistant_response: str,
        analysis_context_summary: Optional[str] = None
    ) -> list[str]:
        # Core logic to construct prompt and call LLM
        pass
    ```
-   **Core Logic:** This service will be responsible for constructing the prompt for the LLM, incorporating `conversation_history`, `last_assistant_response`, and `analysis_context_summary`.
-   It will call an existing or new method in `pdf_processing/api_service.py` to interact with the Anthropic API.

### 3. Integration with `pdf_processing/api_service.py`

-   Leverage existing methods (like `execute_tool_interaction_turn` with `model_override`) or create a new general-purpose method for text generation (e.g., `async def generate_text_response(messages: list, model_override: Optional[str] = None, max_tokens: int = 150) -> str:`).
-   The `suggestion_service.py` would call this method.
-   **Model Selection:** `MODEL_HAIKU` (from `settings.py`) is recommended for this feature for efficiency, passed as `model_override`.

### 4. Prompt Engineering (in `services/suggestion_service.py`)

-   The prompt sent to the LLM needs to be carefully crafted.
-   **Example System Message:**
    "You are an expert financial analyst assistant. Based on the provided conversation history, the assistant's last response, and the current summary of the financial analysis pane, generate three distinct and insightful follow-up questions a user might ask. These questions should help the user explore the topic further, potentially connecting the chat discussion with the data or findings in the analysis pane. Return only the three questions, each on a new line."
-   **Prompt Structure:**
    1.  System Message (as above)
    2.  Conversation History (e.g., last N turns)
    3.  Last Assistant Response: `[last_assistant_response]`
    4.  Current Analysis Pane Summary: `[analysis_context_summary]` (Include this section only if `analysis_context_summary` is provided and not empty)
    5.  Instruction: "Suggest 3 follow-up questions:"
-   The LLM's response will then be parsed in `suggestion_service.py` to extract the three questions.

## II. Frontend Modifications (primarily in `src/components/chat/ChatInterface.tsx`)

### 1. Sourcing `analysis_context_summary`

-   The frontend needs to provide a relevant summary of the analysis pane's content.
-   **Strategies:**
    -   **Option A (Text-based analysis):** Use existing text from the frontend state if the analysis pane displays textual results.
    -   **Option B (Visual/complex analysis):** The analysis pane component generates a concise textual summary of its current view (e.g., chart descriptions) and exposes it via state/props.
    -   **Option C (Backend-generated summary):** When the backend performs an analysis, it also generates a summary for the frontend to store and use.

### 2. API Service Function (Frontend)

-   Create/update an API service function to call `/api/v1/chat/suggest-questions`.
-   It must include `conversation_history`, `last_assistant_response`, and the new `analysis_context_summary` in the payload.
    ```typescript
    async function fetchSuggestedQuestions(
      conversationHistory: Array<{role: string; content: string}>,
      lastAssistantResponse: string,
      analysisContextSummary: string | null
    ) {
      const payload = {
        conversation_history: conversationHistory,
        last_assistant_response: lastAssistantResponse,
        analysis_context_summary: analysisContextSummary,
      };
      // ... make the API POST request
    }
    ```

### 3. State Management for Suggested Questions

-   Add state to `ChatInterface.tsx`:
    ```typescript
    const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
    ```

### 4. Triggering the Suggestion Fetch

-   After a new assistant response is received and displayed:
    1.  Obtain `currentConversationHistory`.
    2.  Obtain `latestAssistantResponse`.
    3.  Obtain `currentAnalysisContextSummary` (from the chosen strategy in II.1).
    4.  Call the frontend `fetchSuggestedQuestions` service.
    5.  Update the `suggestedQuestions` state with the API response.

### 5. Displaying Suggested Questions

-   Conditionally render buttons if `suggestedQuestions.length > 0`.
    ```tsx
    {suggestedQuestions.length > 0 && (
      <div className="mt-2 space-y-1">
        {suggestedQuestions.map((question, index) => (
          <button
            key={index}
            className="p-1 bg-card border border-border rounded-md text-left w-full hover:bg-muted/30 transition-colors text-foreground text-xs"
            onClick={() => handleSuggestedQuestionClick(question)}
          >
            {question}
          </button>
        ))}
      </div>
    )}
    ```

### 6. Handling Suggested Question Clicks

-   Create `handleSuggestedQuestionClick(question: string)`:
    1.  Set the chat input field's value to the clicked question.
    2.  Optionally, automatically submit the question.
    3.  Clear `suggestedQuestions` (they will be re-fetched after the next AI response).

## III. Overall Workflow

1.  User sends a message.
2.  Frontend calls the main chat API.
3.  Backend processes, gets AI response, returns it.
4.  Frontend displays AI response.
5.  **NEW:** Frontend gathers `conversationHistory`, `lastAssistantResponse`, and `analysis_context_summary`.
6.  **NEW:** Frontend calls `/api/v1/chat/suggest-questions` with this data.
7.  **NEW:** Backend's `suggestion_service` (using an LLM, likely Haiku via `pdf_processing.api_service`) generates three questions based on all provided context and returns them.
8.  **NEW:** Frontend receives suggested questions and displays them as clickable buttons.
9.  If user clicks a suggestion, frontend populates input (and optionally submits), repeating the cycle.
