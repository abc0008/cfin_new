# Detailed Implementation Plan: Analysis Service Orchestration & Refactoring

## Problem Statement

The current financial analysis service primarily relies on a single, comprehensive prompt to Claude for various analysis types that may involve multiple tool calls (e.g., for generating several charts, tables, and metrics). This approach has shown limitations:

1.  **Inconsistent Multiple Tool Usage**: Claude may not consistently execute all desired tool calls or generate the full suite of requested artifacts (e.g., multiple distinct charts or tables) from a single, complex prompt. The model might prioritize certain tools or aspects of the prompt, leading to incomplete or less diverse outputs than intended, especially for analysis types that inherently require a sequence of data generation and presentation steps.
2.  **Lack of Specificity**: A generic prompt struggles to guide the model effectively for the nuanced requirements of different analysis types (e.g., a simple sentiment analysis vs. a multi-faceted comprehensive report). This can result in outputs that are not optimally tailored to the user's specific analytical need.
3.  **Scalability and Maintenance**: As more analysis types are added, managing a single, monolithic prompting strategy or a complex conditional logic within one function becomes increasingly difficult, error-prone, and hard to debug.

This plan outlines a phased approach to refactor the `AnalysisService` to:
*   Implement tailored orchestration logic (bespoke system prompts and potentially sequential tool-calling loops) for each `analysis_type`.
*   Adopt a more modular and extensible design using the Strategy pattern for complex analysis types.
*   Clarify the role of `ClaudeService` as a stateless API interaction layer.

## Overall Orchestration Strategy

The core principle of this refactoring is to establish `AnalysisService.run_analysis` as the central router and high-level orchestrator. Based on the incoming `analysis_type`, `run_analysis` will delegate the detailed orchestration to one of two mechanisms:

1.  **Specialized Private Methods within `AnalysisService`**: For simpler, more straightforward analysis types (e.g., `basic_financial`, potentially `sentiment_analysis` if it remains a single-shot call), a dedicated private method like `_orchestrate_basic_financial_analysis(...)` will handle:
    *   Formatting the specific system prompt.
    *   Making one or a short, predefined sequence of calls to `ClaudeService`.
    *   Processing the results.

2.  **Dedicated Strategy Classes**: For more complex analysis types that involve intricate logic, multi-step tool-use sequences, or significant state management during the analysis (e.g., `comprehensive_tools`, `financial_template`), the Strategy design pattern will be employed.
    *   An abstract `AnalysisStrategy` interface will define a common execution method.
    *   Concrete strategy classes (e.g., `ComprehensiveAnalysisStrategy`, `FinancialTemplateStrategy`) will implement this interface, encapsulating the unique orchestration logic for that analysis type.
    *   `run_analysis` will select and instantiate the appropriate strategy.

**`ClaudeService` Role Clarification:**

*   `ClaudeService` will be strictly responsible for direct interactions with the Anthropic Claude API. It will be stateless concerning the analysis orchestration.
*   It will provide standardized methods for making API calls, such as:
    *   `analyze_with_visualization_tools()`: For general, potentially single-shot tool use with the standard financial system prompt.
    *   `analyze_with_financial_analysis_template()`: For the specific, complex template-driven flow (which might internally be a sequence but is exposed as one method for that template).
    *   **(New Proposed Method)** `execute_tool_interaction_turn(system_prompt: str, messages: List[Dict], tools: List[Dict]) -> AnthropicAPIResponse`: A more generic method that allows an orchestrator (a private method in `AnalysisService` or a Strategy class) to manage a conversational loop. It sends the current state of messages and returns Claude's raw response, allowing the caller to process tool calls, tool results, and build the next turn's messages.
*   `ClaudeService` will also handle low-level tool call processing (parsing `ToolUseBlock` and `ToolResultBlock`, basic validation of tool inputs/outputs if necessary, but not the logic of *which* tools to call or *how many times*).
*   Tool definitions (e.g., `ALL_TOOLS_DICT`) will remain centralized, likely in `ClaudeService` or a shared `models.tools` module.

---

**Phase 1: Implement Tailored Orchestration for Simpler Types (In-Place in `AnalysisService`)**

*   **Objective**: Create distinct, simpler orchestrations for `basic_financial` and `sentiment_analysis` directly within `AnalysisService` to quickly improve their reliability and specificity.
*   **Files Affected**:
    *   `cfin/backend/services/analysis_service.py`
    *   `cfin/backend/pdf_processing/claude_service.py` (Potentially for minor adjustments or ensuring methods are suitable for direct calls by orchestrators)

---

### **Analysis Type: `basic_financial`**

*   **Current State**: Currently routed to `claude_service.analyze_with_visualization_tools` with a generic query. This may not reliably produce the desired concise output (text summary, few metrics, one table).
*   **Target Orchestration Logic**:
    *   **Goal**: Generate a concise textual summary, 2-3 key financial metrics (using `generate_financial_metric` tool), and one main summary table (using `generate_table_data` tool).
    *   **System Prompt**: Design a new system prompt, e.g., `BASIC_FINANCIAL_SYSTEM_PROMPT`.
        ```python
        BASIC_FINANCIAL_SYSTEM_PROMPT = """
        You are an AI financial assistant. Your task is to provide a basic financial overview.
        1.  Provide a concise textual summary (2-3 paragraphs) of the key financial highlights from the document. This MUST be your first output.
        2.  Use the 'generate_financial_metric' tool to extract exactly two (2) distinct key financial metrics (e.g., Total Revenue, Net Income).
        3.  Use the 'generate_table_data' tool to create one (1) summary table of important financial figures.
        Ensure your textual summary briefly references the extracted metrics and table.
        Focus on clarity and conciseness.
        """
        ```
    *   **Conversation Flow**: Likely a single, well-crafted call to `claude_service.analyze_with_visualization_tools` (or a direct call to `claude_service.execute_tool_interaction_turn` if more control over the initial message is needed), using the new `BASIC_FINANCIAL_SYSTEM_PROMPT`. The prompt itself guides Claude to use the specified tools a certain number of times.
    *   **Expected Tools**: `generate_financial_metric` (called for 2 metrics), `generate_table_data` (called once).
*   **Implementation Approach**:
    1.  **Add `BASIC_FINANCIAL_SYSTEM_PROMPT`** in `analysis_service.py`.
    2.  In `AnalysisService.run_analysis`:
        *   Add a new `elif analysis_type == "basic_financial":` block.
        *   Inside, call `self.claude_service.analyze_with_visualization_tools(...)` (or `self.claude_service.execute_tool_interaction_turn` followed by `self.claude_service._process_tool_calls` if the former is not flexible enough for passing a custom system prompt without modification).
            *   Pass the `BASIC_FINANCIAL_SYSTEM_PROMPT`.
            *   Pass a user query tailored for this type, e.g., "Provide a basic financial analysis including a summary, two key metrics, and a summary table."
            *   Pass `aggregate_text`, `knowledge_base`, `primary_doc_base64`, `primary_doc_filename`.
        *   Ensure the `result_data` structure aligns with the frontend's expectations (analysis_text, visualizations, metrics).

---

### **Analysis Type: `sentiment_analysis`**

*   **Current State**: Currently routed to `claude_service.analyze_with_visualization_tools` with a generic query.
*   **Target Orchestration Logic**:
    *   **Goal**: Generate a textual sentiment summary, an overall sentiment score (e.g., positive, neutral, negative), and potentially a list of key phrases influencing sentiment. No complex charts/tables are typically needed unless explicitly asked for.
    *   **System Prompt**: Design a new system prompt, e.g., `SENTIMENT_ANALYSIS_SYSTEM_PROMPT`.
        ```python
        SENTIMENT_ANALYSIS_SYSTEM_PROMPT = """
        You are an AI sentiment analysis expert. Analyze the sentiment expressed in the provided financial document text.
        1.  Provide a textual summary of the overall sentiment.
        2.  Determine an overall sentiment score (e.g., "Positive", "Neutral", "Negative").
        3.  Optionally, list a few key phrases or statements that most significantly contribute to this sentiment.
        Present the score clearly. No complex visualizations are required unless the user specifically asks for something like a sentiment trend over sections.
        """
        ```
    *   **Conversation Flow**: Single call to `claude_service.generate_response` (if no tools are needed) or `claude_service.analyze_with_visualization_tools` (if a simple tool like `generate_financial_metric` could be used to structure the "score" in a structured way, or if future enhancements might add a simple chart).
    *   **Expected Tools**: Mostly text-based. Could potentially use `generate_financial_metric` to structure the sentiment score, e.g., `category: "Sentiment"`, `name: "Overall Sentiment"`, `value: "Positive" (or a numeric mapping)`, `unit: "category"`.
*   **Implementation Approach**:
    1.  **Add `SENTIMENT_ANALYSIS_SYSTEM_PROMPT`** in `analysis_service.py`.
    2.  In `AnalysisService.run_analysis`:
        *   Add `elif analysis_type == "sentiment_analysis":` block.
        *   Call an appropriate `ClaudeService` method. If purely textual, `self.claude_service.generate_response` might be sufficient. If a structured score is desired via a tool, then `self.claude_service.analyze_with_visualization_tools` using the new system prompt.
        *   The result processing will need to map Claude's output to `analysis_text`, and potentially `metrics` if the score is structured.

---

**Phase 2: Implement Strategy Pattern for Complex Analysis Types**

*   **Objective**: Refactor complex analysis types (`comprehensive_tools`, `financial_template`, and potentially others like `financial_ratios`, `trend_analysis` if they grow in complexity) into separate Strategy classes for better modularity, testability, and maintainability.
*   **Files Affected**:
    *   `cfin/backend/services/analysis_service.py` (will instantiate and use strategies)
    *   **New Folder**: `cfin/backend/services/analysis_strategies/`
        *   `base_strategy.py` (defines abstract `AnalysisStrategy`)
        *   `comprehensive_strategy.py`
        *   `financial_template_strategy.py`
        *   (Potentially others: `financial_ratios_strategy.py`, `trend_analysis_strategy.py`)
    *   `cfin/backend/pdf_processing/claude_service.py` (to add `execute_tool_interaction_turn` if it doesn't exist, and ensure other methods are suitable).

*   **Steps**:

    1.  **Define `AnalysisStrategy` Interface** (`analysis_strategies/base_strategy.py`):
        ```python
        from abc import ABC, abstractmethod
        from typing import List, Dict, Any
        from models.database_models import Document # Assuming Document model path
        from pdf_processing.claude_service import ClaudeService

        class AnalysisStrategy(ABC):
            @abstractmethod
            async def execute(
                self,
                documents: List[Document], # Pass full Document objects
                aggregate_text: str,
                primary_doc_base64: Optional[str],
                primary_doc_filename: Optional[str],
                parameters: Dict[str, Any],
                claude_service: ClaudeService
            ) -> Dict[str, Any]: # Returns structured result data
                pass
        ```

    2.  **Implement Concrete Strategies**:
        *   For each complex analysis type (starting with `comprehensive_tools` and refactoring `financial_template`):
            *   Create a new file (e.g., `analysis_strategies/comprehensive_strategy.py`).
            *   Define a class (e.g., `ComprehensiveAnalysisStrategy`) inheriting from `AnalysisStrategy`.
            *   Move the orchestration logic (system prompt definition, conversation loop, tool interaction, result processing) for that `analysis_type` from `AnalysisService.run_analysis` into the `execute` method of its strategy class.
            *   Strategies will use `claude_service.execute_tool_interaction_turn` for managing multi-turn conversations or `claude_service.analyze_with_visualization_tools` for simpler, single-shot interactions if appropriate for that strategy.

    3.  **Refactor `ClaudeService` (if needed)**:
        *   Implement `execute_tool_interaction_turn(self, system_prompt: str, messages: List[Dict], tools: List[Dict]) -> AnthropicMessage`:
            *   This method makes a single call to `self.client.messages.create(...)`.
            *   It takes the current conversation `messages` (which the strategy will build and maintain).
            *   It returns the raw `AnthropicMessage` object, allowing the strategy to inspect `stop_reason`, `content` (text and tool_use blocks), and decide on the next step (e.g., formulate tool results, append to messages, call again, or finish).
        *   Ensure `_process_tool_calls` or a similar utility is available (perhaps in `ClaudeService` or a helper module) for strategies to use if they call `execute_tool_interaction_turn` and need to process the resulting `AnthropicMessage`.

    4.  **Update `AnalysisService.run_analysis`**:
        *   Create a mapping of `analysis_type` to Strategy classes.
        *   For analysis types handled by strategies:
            *   Instantiate the appropriate strategy.
            *   Call its `execute` method, passing necessary arguments (documents, aggregate_text, parameters, `self.claude_service`).
            *   The existing logic for saving results via `analysis_repository` remains in `run_analysis`.

    5.  **Refactor `financial_template`**:
        *   The existing sequential orchestration for `financial_template` within `AnalysisService.run_analysis` will be moved into a `FinancialTemplateStrategy` class.
        *   This strategy will utilize the `financial_analysis_template` string (which can remain defined in `analysis_service.py` or moved to the strategy).

---

### **Analysis Type: `comprehensive_tools` (as a Strategy)**

*   **Current State**: Uses `claude_service.analyze_with_visualization_tools` with a generic prompt.
*   **Target Orchestration Logic (within `ComprehensiveAnalysisStrategy.execute`)**:
    *   **Goal**: Provide a truly comprehensive analysis using multiple tools as appropriate, guided by a detailed system prompt and potentially a multi-turn conversation if the initial query is broad or implies iterative refinement.
    *   **System Prompt**: The existing `FINANCIAL_ANALYSIS_SYSTEM_PROMPT` in `claude_service.py` is a good starting point but might be moved to/customized within the strategy if it becomes highly specific to this strategy's flow.
    *   **Conversation Flow**:
        *   Could start with a call to `claude_service.analyze_with_visualization_tools` if the query is specific enough for a single comprehensive shot.
        *   OR, for very broad queries ("analyze this document"), the strategy might implement a short loop:
            1.  Initial call to get a high-level analysis and identify key areas/tools.
            2.  Follow-up calls to delve deeper into specific areas or request more visualizations based on the first response. This would use `claude_service.execute_tool_interaction_turn`.
    *   **Expected Tools**: `generate_graph_data`, `generate_table_data`, `generate_financial_metric` – used liberally as dictated by the document content and the aim for "comprehensiveness."
*   **Implementation Approach**:
    1.  Create `ComprehensiveAnalysisStrategy` in `analysis_strategies/comprehensive_strategy.py`.
    2.  Implement its `execute` method. This method will contain the logic for:
        *   Defining/retrieving the appropriate system prompt (e.g., `FINANCIAL_ANALYSIS_SYSTEM_PROMPT`).
        *   Preparing the initial messages for Claude.
        *   Calling `self.claude_service.analyze_with_visualization_tools(...)` or initiating a loop with `self.claude_service.execute_tool_interaction_turn(...)`.
        *   Accumulating results (text, charts, tables, metrics) across turns if a loop is used.
        *   Returning the consolidated `result_data`.

---

**Phase 3: Iteratively Refine Other Analysis Types**

*   **Objective**: Apply the chosen orchestration approach (specialized method in `AnalysisService` or dedicated Strategy class) to other existing analysis types like `financial_ratios`, `trend_analysis`, and `benchmarking`.
*   **Files Affected**:
    *   `cfin/backend/services/analysis_service.py`
    *   `cfin/backend/services/analysis_strategies/` (if new strategies are created)

*   **Steps (for each remaining type)**:
    1.  **Evaluate Complexity**: Decide if a simple private method in `AnalysisService` is sufficient or if a full Strategy class is warranted.
    2.  **Define Target Logic**:
        *   Specific goals for the analysis type.
        *   Tailored system prompt.
        *   Expected conversation flow (single call vs. loop).
        *   Key tools to be utilized.
    3.  **Implement**: Create the private method or Strategy class.
    4.  **Integrate**: Update `AnalysisService.run_analysis` to delegate to the new implementation.
    5.  **Test**: Thoroughly test the refined analysis type.

---

## Frontend Impact & API Contract

*   **Analysis Type Definitions**:
    *   The list of `SUPPORTED_ANALYSIS_TYPES` in `AnalysisService` (backend) must be kept in sync with the analysis type definitions used in the frontend (e.g., in `AnalysisTypeSelector.tsx` or a shared types file like `app_types.ts`).
    *   The `type` field (e.g., "comprehensive_tools", "basic_financial") is the key string exchanged.
*   **API Call for Running Analysis**:
    *   The frontend will continue to call the existing `/api/analysis/run` (or similar) endpoint, providing `document_ids`, `analysis_type`, and optional `parameters` (query, knowledge_base).
    *   The backend refactoring described in this plan should be **transparent** to this API contract. The internal orchestration changes, but the endpoint signature and the primary way of triggering an analysis remain the same.
*   **Result Structure**:
    *   The overall structure of the analysis result returned by the API (and subsequently used by the frontend to display analysis) should remain consistent. This typically includes fields like `analysis_id`, `analysis_text`, `visualization_data` (with `charts`, `tables`), `metrics`, `document_ids`, `timestamp`, etc.
    *   While the *content* of these fields will be improved and more reliable due to tailored orchestration, the *schema* of the response should be preserved as much as possible to minimize breaking changes on the frontend. If new structured data is added (e.g., a dedicated "sentiment_score" field), the frontend will need to be updated to utilize it.

---

## Testing Strategy

*   **Unit Tests**:
    *   For `ClaudeService` methods (mocking `AsyncAnthropic` client).
    *   For individual `AnalysisStrategy` classes (mocking `ClaudeService`).
    *   For specialized private orchestration methods in `AnalysisService`.
*   **Integration Tests**:
    *   Test the `AnalysisService.run_analysis` router with different `analysis_type` values, ensuring delegation to the correct method/strategy.
    *   Test the full flow from `run_analysis` through `ClaudeService` to (mocked) API calls for key analysis types.
*   **End-to-End (E2E) / Manual Tests**:
    *   Crucial for verifying that the actual output from Claude, when using the new prompts and orchestration, meets the desired quality and includes the expected artifacts (text, charts, tables, metrics).
    *   Test with representative financial documents and queries for each analysis type.
    *   Verify that the frontend correctly displays results from the refactored backend.

---

This plan provides a structured path towards a more robust, maintainable, and effective `AnalysisService`. Each phase should be implemented and tested thoroughly. 