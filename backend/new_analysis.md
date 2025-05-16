# 📚 Storybook Implementation Outline  
_Each bullet represents **one story point (1 SP)**.  Follow the flow top-to-bottom; stories are intentionally tiny for easy slicing or re-ordering during sprint planning._

| ✓ | # | File / Folder | Story / Acceptance Criteria | "Done" Code Changes |
|---|----|---------------|-----------------------------|---------------------|
| [x] | **1** | `analysis_service.py` | **Router delegates to strategies**<br>AC: `run_analysis()` maps `comprehensive_tools` & `financial_template` to classes in `analysis_strategies`. | Implemented router logic in `run_analysis` to delegate to strategy classes based on `analysis_type` using `strategy_map`. Instantiates and executes the selected strategy. |
| [x] | **2** | `analysis_service.py` | **Controlled sequential flows for basic types**<br>AC: `basic_financial` & `sentiment_analysis` remain handled within `AnalysisService`. Monolithic `comprehensive_tools` branch removed. These basic flows use distinct system prompts (e.g., `BASIC_FINANCIAL_SYSTEM_PROMPT`) AND a controlled, sequential interaction model (e.g., 2-4 turns) via `ClaudeService.execute_tool_interaction_turn`. Each prompt MUST explicitly instruct Claude on the exact number/type of tool invocations (e.g., 'call `generate_financial_metric` twice, then `generate_table_data` once'). Flows MUST return a `Dict[str, Any]` conforming to the standard result structure (analysis_text, visualizations, metrics). | Implemented direct handling for `basic_financial` and `sentiment_analysis` in `AnalysisService.run_analysis` using `execute_tool_interaction_turn` in a loop (max 4 turns). Defined `BASIC_FINANCIAL_SYSTEM_PROMPT` and `SENTIMENT_ANALYSIS_SYSTEM_PROMPT` to guide sequential tool calls and ensure consistent result structure. Old comprehensive block removed by new routing. |
| [x] | **3** | _new_ `services/analysis_strategies/` | **Create strategy package**<br>AC: Folder with `__init__.py`. | Created `services/analysis_strategies/` directory and an `__init__.py` file to establish it as a Python package. |
| [x] | **4** | `analysis_strategies/base_strategy.py` | **Expose common interface with structured return**<br>AC: `class AnalysisStrategy(ABC)` w/ async `execute(…)`. The `execute` method MUST return a `Dict[str, Any]` adhering to the standard structure: `{"analysis_text": str, "visualizations": {"charts": List[ChartData], "tables": List[TableData]}, "metrics": List[FinancialMetric]}` to ensure consistency. | Defined abstract base class `AnalysisStrategy(ABC)` in `base_strategy.py` with an `__init__(self, claude_service: ClaudeService)` and an abstract async method `execute(...)` type-hinted to return `Dict[str, Any]` (analysis_text, visualizations, metrics). |
| [x] | **5** | `analysis_strategies/__init__.py` | **Lookup map exists**<br>AC: `strategy_map = {"comprehensive_tools": ComprehensiveAnalysisStrategy, "financial_template": FinancialTemplateStrategy}`. | In `analysis_strategies/__init__.py`, imported concrete strategy classes (`ComprehensiveAnalysisStrategy`, `FinancialTemplateStrategy`) and defined `strategy_map` dictionary to map analysis type strings to corresponding strategy classes. |
| [x] | **6** | `analysis_strategies/comprehensive_strategy.py` | **Multi-turn comprehensive analysis**<br>AC: Loops ≤7 turns using `claude.execute_tool_interaction_turn`, handles tool blocks, accumulates `text/charts/tables/metrics`. | Implemented `ComprehensiveAnalysisStrategy` in `comprehensive_strategy.py`. Defined `COMPREHENSIVE_SYSTEM_PROMPT`. The `execute` method loops up to 7 turns, calling `claude_service.execute_tool_interaction_turn` and processing tool results via `tool_processing.process_visualization_input` to accumulate text, charts, tables, and metrics. Returns a standard result dictionary. |
| [x] | **7** | `analysis_strategies/financial_template_strategy.py` | **Encapsulate template flow**<br>AC: Old `_financial_template` logic moved here, returns result instead of DB write. | Implemented `FinancialTemplateStrategy` in `financial_template_strategy.py`. Moved `FINANCIAL_ANALYSIS_TEMPLATE_PROMPT` into this class. The `execute` method mirrors `ComprehensiveAnalysisStrategy`'s loop structure (max 7 turns), using `claude_service.execute_tool_interaction_turn` and `tool_processing.process_visualization_input`, and returns a standard result dictionary. |
| [x] | **8** | `claude_service.py` | **Single-turn helper with tuning params**<br>AC: `async execute_tool_interaction_turn(system_prompt, messages, tools=None, max_tokens=4096, temperature=0.3)` includes `max_tokens` and `temperature` in its signature, allowing callers to specify these per turn. Returns Claude raw response. Defaults: `ALL_TOOLS_DICT`, `tool_choice="auto"`, `beta_headers=["token-efficient-tools-2025-02-19"]`. | Added `async def execute_tool_interaction_turn(...)` to `ClaudeService.py`. The method accepts `system_prompt`, `messages`, `tools`, `max_tokens`, and `temperature`. It calls `self.client.messages.create` with `tool_choice="auto"` and token-efficient headers, returning the raw `AnthropicMessage`. |
| [x] | **9** | `claude_service.py` → `_process_visualization_input` | **Public helper(s) for strategies**<br>AC: Parsing utilities become static methods or move to `utils/tool_processing.py`. | Created `utils/tool_processing.py`. Moved processing logic for `generate_graph_data`, `generate_table_data`, and `generate_financial_metric` from `ClaudeService` into `tool_processing.py` as `process_chart_input`, `process_table_input`, `process_financial_metric_input`. A new router function `process_visualization_input` in `tool_processing.py` calls these. `AnalysisService` and strategy classes updated to use these. Original private methods in `ClaudeService` targeted for removal. |
| [x] | **10** | `models/tools.py` (new) | **Centralize tool schemas**<br>AC: `ALL_TOOLS_DICT` lives here. | Centralized tool definitions in `models/tools.py`. `ToolSchema` now includes an optional `processor: Callable`. `ALL_TOOLS_DICT` maps tool names to `ToolSchema` instances, linking to processing functions in `utils.tool_processing`. `CLAUDE_API_TOOLS_LIST` provides schemas for API calls. `ClaudeService` updated to use `CLAUDE_API_TOOLS_LIST` for API calls and `ALL_TOOLS_DICT` (via `self.tool_schemas_map`) to invoke processors in `_process_tool_calls`. |
| [x] | **11** | `tests/unit/strategies/test_comprehensive_strategy.py` | **Unit coverage**<br>AC: Mock Claude; assert ≥1 chart & summary text returned. | Created `test_comprehensive_strategy.py`. Added `test_comprehensive_strategy_returns_chart_and_text` which mocks `ClaudeService.execute_tool_interaction_turn` to simulate a multi-turn interaction involving a `generate_graph_data` tool call. Also mocks `tool_processing.process_visualization_input`. Asserts that the strategy returns accumulated text and at least one chart. |
| [x] | **12** | `tests/unit/services/test_analysis_service_router.py` | **Router unit test**<br>AC: `run_analysis("comprehensive_tools")` instantiates `ComprehensiveAnalysisStrategy`. | Created `test_analysis_service_router.py`. Added tests to verify that `AnalysisService.run_analysis` correctly instantiates and calls the `execute` method of the appropriate strategy (`ComprehensiveAnalysisStrategy`, `FinancialTemplateStrategy`) based on `analysis_type` by patching `strategy_map`. Also tested handling of unknown strategy types. |
| [x] | **13** | `README.md` | **Dev documentation with prompt guidance**<br>AC: Section "Adding a new Analysis Strategy". Includes best practices for prompt engineering, emphasizing the 'Tool Choreography' technique (enumerated, imperative steps for exact tool calls) to ensure deterministic tool use by Claude. | Added "Adding a new Analysis Strategy" section to `README.md`. This section provides a 4-step guide (Define class, Register, Define tools/processors, Test) with code examples. It also includes detailed prompt engineering best practices, with a specific subsection on "Tool Choreography" explaining how to guide Claude for deterministic multi-tool sequences. |
| [x] | **14** | `cfin/.github/workflows/python-ci.yml` | **CI runs new tests with coverage gate**<br>AC: `pytest` path includes strategy folder. CI job fails if test coverage drops below 85%. | Created `cfin/.github/workflows/python-ci.yml`. The workflow installs dependencies, runs `pytest` from the `cfin/backend/` directory (covering `tests/unit/`), calculates coverage for `services`, `models`, `utils`, and `pdf_processing` modules, and includes `--cov-fail-under=85` to enforce the coverage minimum. |
| [x] | **15** | `Frontend: AnalysisCanvas.tsx / relevant components` | **Graceful display for missing artifacts**<br>AC: Frontend components displaying analysis results (charts, tables, metrics) MUST gracefully handle cases where these arrays/objects are empty or undefined. Display user-friendly messages like "No charts generated," "No tables available," or "No metrics generated" instead of crashing or showing empty spaces. Response schema from backend remains consistent. | Verified that `cfin/nextjs-fdas/src/components/visualization/Canvas.tsx` (which uses `ChartRenderer`, `TableRenderer`) and `cfin/nextjs-fdas/src/components/metrics/MetricGrid.tsx` already implement graceful handling for empty or undefined arrays of charts, tables, and metrics. Specific "No charts/tables/metrics available" messages are displayed within the respective UI sections. No code changes were required. |
| [x] | **16** | `claude_service.py` | **Implement retry with back-off for API calls**<br>AC: Wrap calls to `self.client.messages.create` (esp. within `execute_tool_interaction_turn`) with a retry mechanism (e.g., exponential back-off for 5xx or rate limit errors) for up to 3-5 attempts. | Added `@backoff.on_exception` decorator to `ClaudeService.execute_tool_interaction_turn`. Configured for exponential backoff (max 5 tries) on `anthropic.APIStatusError`, `anthropic.APITimeoutError`, and `anthropic.RateLimitError`. Imported `backoff` and necessary Anthropic exceptions. Assumed `backoff` is added to project dependencies. |
| [x] | **17** | `claude_service.py` / Strategies / `analysis_service.py` | **Handle tool schema validation errors robustly**<br>AC: If Pydantic validation fails on tool input/output (e.g., in `_process_visualization_input` or strategy-level parsing), raise a specific custom exception (e.g., `ToolSchemaValidationError`). `AnalysisService.run_analysis()` MUST catch this and return a 422 HTTP error with a clear message. | Created `cfin/backend/utils/exceptions.py` with `ToolSchemaValidationError`. Updated parsing functions in `cfin/backend/utils/tool_processing.py` (e.g., `process_chart_input`) to catch Pydantic `ValidationError` and raise `ToolSchemaValidationError`. Modified `AnalysisService.run_analysis()` to `try...except ToolSchemaValidationError` around strategy execution and basic_financial/sentiment_analysis tool processing, then raise `HTTPException` with status 422 and a detailed error message. Imported `HTTPException` and `ToolSchemaValidationError` in `analysis_service.py`. Removed `ToolResultBlock` import from `claude_service.py` to fix an unrelated startup import error. |
| [x] | **18** | `Database / Alembic` & `cfin/.github/workflows/python-ci.yml` | **Migrate visualization/metrics storage to JSONB**<br>AC: Create and commit an Alembic migration script to change columns storing chart, table, and metric arrays/JSON to JSONB type in PostgreSQL. CI pipeline includes a step to test `alembic upgrade head` and `alembic downgrade -1` (or equivalent). | Provided an Alembic migration script to change the `result_data` column in the `analysis_results` table to `JSONB` for PostgreSQL. Updated `cfin/.github/workflows/python-ci.yml` to include steps for setting up a PostgreSQL service and running Alembic migration smoke tests (`upgrade head`, `downgrade -1`, `upgrade head`). Also advised adding `backoff` to `requirements.txt` to resolve an import error. |

# Comprehensive Analysis Strategy

Great. I'll review the `Analysis_Service.py` and `Claude_Analysis.py` files in your `abc0008/cfin_new` repo to understand the current orchestration and how analysis types (especially `comprehensive_tools`) are processed. I'll then cross-reference this with Anthropic's Claude tool use documentation and notebooks to design a detailed strategy and implementation plan.

The goal is to enable multi-step, complex prompts that reliably trigger multiple tool calls (charts, metrics, text) and render as a single artifact—especially for the comprehensive analysis type using your structured prompt format and response plan.

I'll get started and let you know when the plan is ready.


# Multi-Step Analysis Orchestration Design and Plan

## Limitations of the Current Monolithic Prompt Strategy

The existing implementation often uses a single, all-in-one prompt to Claude for complex analyses. This **single-shot approach** has notable drawbacks:

* **Incomplete Multi-Tool Usage:** In one big prompt, Claude may not execute all desired tool calls. For example, it might generate only one chart or table even if multiple were intended. The model tends to focus on certain parts of the request and skip others, leading to **inconsistent or partial outputs**. In short, a single complex prompt can yield less diverse artifacts than expected (e.g. missing some charts or metrics).

* **Lack of Analysis-Type Specificity:** A one-size-fits-all prompt cannot optimally guide the model for different analysis needs. A broad *comprehensive analysis* vs. a narrow *sentiment analysis* require different emphasis, but a generic prompt may produce suboptimal results for each. The current approach struggles to tailor outputs to the nuanced requirements of each `analysis_type`, sometimes giving overly general or irrelevant information.

* **Poor Scalability & Maintainability:** As more analysis types are added, having all logic in one monolithic prompt or one function becomes **hard to manage and debug**. It's difficult to conditionally handle many analysis modes in one place. This reduces clarity and increases the risk of errors when extending the system.

These limitations motivate a refactor toward a **multi-turn, modular orchestration** strategy, allowing the model to handle complex queries stepwise and with prompts specialized per analysis type.

## Current Claude Tool Usage in the Code

Today's implementation uses Anthropic Claude's tool API in both single-turn and iterative fashions. For *comprehensive* analysis, the code currently calls Claude with all tools enabled in one go (monolithic call). For the custom `financial_template` flow, it runs Claude in a loop, handling one tool invocation at a time.

### Single-Call (Monolithic) Usage:
**Single-Call (Monolithic) Usage:** In the `comprehensive_tools` flow, the code prepares a user message containing the document content, knowledge base, and query, then calls `ClaudeService.analyze_with_visualization_tools()`. This method sets a system prompt (guiding Claude to use tools) and sends a single user message with all context. It includes **all tool definitions** (`ALL_TOOLS_DICT`) with `tool_choice={"type": "auto"}`, allowing Claude to decide when to use each tool. The model's response may contain multiple content blocks – typically one **text block** (the narrative analysis) and possibly several **`tool_use` blocks** if it attempts charts/tables/metrics. The code then processes the response in one pass by extracting each tool's JSON payload and converting it into structured data. For example, `_process_tool_calls` iterates through `response.content` and for each `ToolUseBlock` (e.g. a `generate_graph_data` call), it parses the `block.input` into a chart/table structure. All extracted charts and tables, along with any text, are collected into the result. This yields a final combined result but **without iterative back-and-forth** – if Claude didn't produce all desired tool outputs in that one response, they'll be missing. (Notably, if Claude stops mid-response to request a tool result, the current single-call implementation wouldn't catch it because it doesn't loop on `stop_reason`.)

### Iterative Tool Invocation (Multi-turn):
* **Iterative Tool Invocation (Multi-turn):** The `financial_template` analysis type demonstrates a more robust orchestration. Here, the system uses a long, structured system prompt (the provided financial analysis template) and then enters a loop of up to 7 turns. In each iteration, the code calls `ClaudeService.client.messages.create()` with the current conversation state and tools enabled. When Claude's response contains a `tool_use` request (e.g. asking to `generate_graph_data`), the code intercepts it before Claude continues. The implementation logs each `ToolUseBlock` (which has a `name`, `id`, and `input` payload), executes the corresponding Python function (to generate the actual chart/table data) via `_process_visualization_input`, and then packages the result into a `ToolResultBlock`. Specifically, it appends a new **user message** with content of type `"tool_result"` carrying the JSON output (or error) for that tool call. Claude is then called again with this updated conversation, allowing it to incorporate the tool result and continue the analysis. This loop continues until Claude signals completion (e.g. `stop_reason == "stop_sequence"` or similar). Throughout this process, the code accumulates all text, chart data, table data, and metrics across turns. At the end, it consolidates them into a single `result_data` structure with keys for `analysis_text`, `visualizations.charts`, `visualizations.tables`, and `metrics`.

### Use of Tool Blocks:
* **Use of Tool Blocks:** Under the hood, the Anthropic SDK represents each tool interaction as structured blocks. The current code handles these blocks explicitly:

#### ToolUseBlock
  * **ToolUseBlock:** Represents Claude's invocation of a tool. The code checks for blocks with `block.type == "tool_use"` in the assistant's response. It logs the tool name and input, then feeds this input into the appropriate backend function (e.g., chart or table generator).

#### ToolResultBlock
  * **ToolResultBlock:** Represents the reply to a tool call. After computing the result, the code creates a dict `{"type": "tool_result", "tool_use_id": <ID>, "content": <JSON string>}` and injects it as the next user turn. This signals to Claude the outcome of its tool request (the `tool_use_id` ties the result back to the original call). Claude can then continue the conversation, presumably using the data provided.

Overall, the **current architecture** uses the Claude tools API directly but in an ad-hoc way: one part of the code (`analyze_with_visualization_tools`) uses a single-shot call (which, as noted, risks incomplete results), while another (`financial_template` loop) manually orchestrates multiple turns. This indicates a need for a more unified, high-level orchestration layer on top of Claude's tool API to reliably handle multi-tool interactions.

## Strategy Pattern for Analysis Orchestration

To address the above issues, we propose refactoring the orchestration logic using the **Strategy pattern**, with a dedicated strategy class for each complex analysis type. The idea is to modularize how each analysis is carried out, allowing tailored prompts and multi-turn logic per type without cluttering one giant function.

### Proposed Code Structure:
**Proposed Code Structure:** A new package (e.g. `backend/services/analysis_strategies/`) will house these strategy classes. Key components include:

### Base Strategy Interface:
* **Base Strategy Interface:** An abstract class `AnalysisStrategy` defining a common interface (e.g. an `execute()` coroutine). It will accept the necessary inputs (the document data, aggregated text, optional PDF base64, user query/parameters, and a reference to the ClaudeService) and return the structured result (analysis text + visuals + metrics). This provides a consistent contract for all strategies.

### Concrete Strategy Classes:
* **Concrete Strategy Classes:** For each complex `analysis_type`, a concrete implementation will encapsulate that analysis's logic. For example, a `ComprehensiveAnalysisStrategy` will handle `"comprehensive_tools"` requests, and a `FinancialTemplateStrategy` will handle the `"financial_template"` flow. We might later introduce `TrendAnalysisStrategy`, `BenchmarkingStrategy`, etc., if those analysis types require complex orchestration. Simpler types (like a basic one-off ratio calculation) can remain handled directly in `AnalysisService` or via a simpler strategy.

### Location of Components:
* **Location of Components:** Each strategy lives in its own module (e.g. `comprehensive_strategy.py`, `financial_template_strategy.py` in the `analysis_strategies` folder) and includes any prompt definitions or helper logic specific to that analysis. The existing large prompt template (the multi-step financial analysis instructions) can be moved into the `FinancialTemplateStrategy` or kept in a shared config, but that strategy will be responsible for using it appropriately.

In this design, `AnalysisService.run_analysis()` becomes a **router**. It will map the `analysis_type` to the corresponding strategy. For instance, `if analysis_type == "comprehensive_tools": strategy = ComprehensiveAnalysisStrategy(); result = await strategy.execute(...)`. The service will provide the documents and any pre-processed content (like aggregated text or encoded PDF) to the strategy. Once the strategy returns the `result_data`, `AnalysisService` continues to handle persistence (storing results via the repository) and any post-processing. This clean separation means adding a new analysis type mostly involves adding a new strategy class and updating the mapping, without touching the core logic for others.

Each **Strategy class** implements the orchestration for its analysis type:

### Tailored System Prompt:
* **Tailored System Prompt:** The strategy defines or selects a system prompt optimized for that analysis. For example, the comprehensive analysis strategy can use the existing `FINANCIAL_ANALYSIS_SYSTEM_PROMPT` (which instructs Claude to always produce a text summary and use tools for charts/tables). The `FinancialTemplateStrategy` will use the more elaborate multi-section template (the one with `<financial_analysis_planning>` and structured `<response>` format) to guide Claude step-by-step. By customizing the system instructions, we ensure Claude's behavior is tuned to the specific task at hand (resolving the **lack of specificity** issue). These prompts can live as constants within the strategy classes or a config module.

### Execute Method Logic:
* **Execute Method Logic:** Inside `execute()`, the strategy will orchestrate the Claude interactions. Simpler strategies might make a single call to `ClaudeService` and be done (similar to the current `generate_response` or `analyze_with_visualization_tools` usage). Complex strategies will implement a loop to manage multiple turns. Crucially, the strategy can leverage a new ClaudeService helper for stepping through tool interactions.

## Controlled Multi-Turn Tool Interaction

To support multi-step dialogues with Claude (where the model can call multiple tools sequentially), we will introduce a method like `ClaudeService.execute_tool_interaction_turn(...)`. This method essentially wraps the Anthropic API call for one turn, making it easier for our strategies to drive the conversation. Key aspects of this approach:

### ClaudeService as a Stateless API Layer:
* **ClaudeService as a Stateless API Layer:** The ClaudeService will remain focused on low-level API calls and response parsing, not on decision-making. The new `execute_tool_interaction_turn(system_prompt, messages, tools)` will simply call `self.client.messages.create()` with the given system prompt, current message list, and tools (likely always using `ALL_TOOLS_DICT` and `tool_choice: auto`). It returns Claude's raw response (the `AnthropicMessage` or equivalent) for that turn. This design lets the strategy class decide **when to call the API, how to build the prompt/messages, and what to do after each response** – giving us full control over multi-turn logic outside the ClaudeService.

### Iterative Loop in Strategies:
* **Iterative Loop in Strategies:** A complex strategy (like comprehensive or the template) will manage a loop somewhat like the current `financial_template` flow, but in a cleaner, more flexible way. For example, `ComprehensiveAnalysisStrategy.execute` might do something like:

#### Initial Call:
  1. **Initial call:** Send Claude the user query and document(s) context with a comprehensive analysis system prompt. If the query is very broad ("Analyze everything about this document"), Claude's first response might call for multiple tools or outline a plan. If the model immediately returns a complete answer with all tools used (stop_reason = `stop_sequence`), the strategy can finish. But if Claude stops after invoking a tool (stop_reason = `tool_use`), the strategy will catch that.

#### Tool Result Handling:
  2. **Tool result handling:** The strategy inspects the response content. For any `tool_use` blocks, it uses ClaudeService's existing processing to generate the actual result (chart data, table data, etc.), similar to how `_process_visualization_input` works now. Each result is then added to the `messages` list as a `tool_result` user message. (The logic for constructing these blocks remains the same as current: include the `tool_use_id` and JSON content.)

#### Next Turn:
  3. **Next turn:** With the tool results now in the conversation, the strategy calls `execute_tool_interaction_turn` again to continue the dialogue. Claude will incorporate the provided tool outputs and either produce further analysis (maybe invoking another tool) or conclude the answer.

#### Loop Control:
  4. **Loop control:** The loop continues until Claude indicates the conversation is complete. This is typically when `api_response.stop_reason` is `"stop_sequence"` or `"end_turn"` (meaning Claude has finished its answer). We will also have a safety max-turn limit (to avoid infinite loops – e.g., 5-7 turns as in the current code).

Using this controlled turn-by-turn approach ensures **every tool invocation is handled**. The model can generate multiple charts, tables, and metrics in sequence, each time pausing for the backend to supply the data, then resuming. This addresses the inconsistency of the single-shot method by making tool use deterministic and reliable – Claude can't skip a chart because we'll keep the dialogue going until all planned outputs are delivered. It also aligns with Anthropic's intended usage pattern for tools (very similar to how one would handle function calls in OpenAI agents or the examples in Anthropic's `tool_use_with_pydantic` and `vision_with_tools` notebooks, where the assistant calls a tool, receives results, and continues). In fact, this strategy pattern is essentially implementing a lightweight **agent loop** on top of Claude.

### Example – Comprehensive Tools Strategy:
**Example – Comprehensive Tools Strategy:** As outlined in the planning notes, the comprehensive strategy could even do an initial one-shot attempt and then fall back to a loop if needed. For instance, if the user query is specific ("Chart the revenue trend for 2020-2023"), a single call might suffice. But if it's broad, the strategy can detect that and use a multi-turn approach. This kind of adaptive orchestration (perhaps first asking Claude for a plan or key areas, then diving deeper) can be implemented within the strategy's execute method. The important part is we now have the flexibility to do so without cluttering `AnalysisService` or duplicating code.

## Consolidated Outputs and Final Artifacts

Each strategy will assemble the final results from the multi-turn interaction into a unified response object, similar to the current `result_data` structure. After the loop finishes, the strategy will collate:

### Textual Analysis:
* **Textual Analysis:** All the narrative text produced by Claude across turns (or in the final answer). In practice, Claude's first response block is mandated to be a comprehensive text summary (our system prompt explicitly instructs this). We will ensure we capture that. The strategies might simply accumulate `assistant_text` from each turn's `text` blocks into one `analysis_text` string (the current code already appends text blocks sequentially). Alternatively, if Claude rewrites the summary at the end, we might use the final version. Regardless, the result will include a clear textual report of findings.

### Visualizations (Charts/Tables):
* **Visualizations (Charts/Tables):** All JSON outputs from `generate_graph_data` and `generate_table_data` calls will be collected. The strategy can maintain lists of charts and tables (as the current loop does with `accumulated_charts`/`accumulated_tables`). Each time a tool result is processed, the returned structured data (which adheres to our Pydantic models for charts or tables) is appended to the respective list. At the end of the loop, these lists are included in the result dictionary under `"visualizations": {"charts": [...], "tables": [...]}`.

### Metrics (Key Figures):
* **Metrics (Key Figures):** Similarly, any outputs from the `generate_financial_metric` tool (individual metrics or KPIs) are collected in a `metrics` list. These might correspond to "cards" in the frontend – small standalone values with labels (e.g., *Total Revenue: \$5M*). By capturing them separately, the frontend can render them as highlight cards. The new orchestration will fully support this, ensuring that if Claude calls `generate_financial_metric` for several items, we capture them all.

### Insights or Other Structured Sections:
* **Insights or Other Structured Sections:** The provided analysis template suggests sections like *Key Findings*, *Recommendations*, *Suggested Next Actions* within the final `<response>`. Our design will enable producing such sections as part of the text output. Since the template instructs the assistant to structure the final answer with clearly labeled parts (Query Restatement, Approach, Artifact with charts and insights, etc.), the `FinancialTemplateStrategy` will simply let Claude produce that formatted answer (the model is guided to do so by the prompt). We don't need to parse these sections explicitly on the backend – we can treat it as one big `analysis_text` (or possibly split by headings if needed for UI). The key point is that **all content – narrative and visualization data – is present in the strategy's result**, ready for the frontend to render an integrated analysis artifact.

By having one strategy return one result object, we ensure the response is **consolidated**. The front-end or API consumer will not have to assemble pieces from multiple calls; it will receive a single payload containing the text analysis and all charts/tables/metrics. This aligns exactly with the user's desired end-state: "a single visualization artifact containing all proposed charts, graphs, and text blocks". The new system will thus deliver that artifact complete with rich content (multiple charts, tables, key metrics) and the explanatory text, following the structured format outlined in the prompt template.

## Alignment with Anthropic Best Practices

This redesigned approach is informed by Anthropic's best practices for tool use and efficient prompt design:

### Multi-Turn Tool Use for Completeness:
* **Multi-Turn Tool Use for Completeness:** Instead of expecting the model to cram everything into one huge response, we let it proceed step by step. This is analogous to patterns in Anthropic's examples (e.g., the model calls a tool, gets data, then continues). It improves reliability – each tool invocation is handled immediately, reducing the chance the model "forgets" to use a tool or produces malformed JSON later. The use of `stop_reason` to control turns is exactly how the Claude API is intended to manage tool interactions in a conversation loop.

### Token Efficiency:
* **Token Efficiency:** We will leverage Claude 3.7's *token-efficient tools* mode. The code already sets the `beta_headers=["token-efficient-tools-2025-02-19"]` when calling the API, and uses the `claude-3-7-sonnet` model optimized for tool usage. This means the system is tuned to not waste tokens when exchanging tool calls (e.g., the prompt and tool schemas are handled more efficiently). By splitting a complex task into turns, we also avoid the model having to regenerate lengthy content multiple times if something changes – it can focus on one piece at a time, which is inherently token-efficient.

### Strict Tool Schemas (Pydantic):
* **Strict Tool Schemas (Pydantic):** The tools are defined with Pydantic models (e.g., `ChartGenerationInputSchema`, `TableGenerationInputSchema`) and we provide their JSON schemas to Claude in `ALL_TOOLS_DICT`. The system prompt even emphasizes: "adhere strictly to the Pydantic models provided in the tool descriptions... pay close attention to required fields and data types". This encourages Claude to produce well-structured JSON that our backend can parse. Our plan retains this practice. In fact, by catching each tool call as it happens, we can validate the JSON against the schema immediately (and if needed, log or even correct minor issues in a future enhancement). The approach from Anthropic's `tool_use_with_pydantic` demo – ensuring the model's outputs conform to a schema – is thus baked into our design via these tool definitions and instructions.

### Dedicated Text vs Tool Output:
* **Dedicated Text vs Tool Output:** Best practices suggest the assistant should not just spit out raw numbers or JSON – it should also provide analysis in natural language. Our system prompt explicitly requires a **comprehensive textual analysis as the first block** of Claude's response. The new orchestration enforces this by design (the first model message in comprehensive analysis is expected to be a `text` block with the summary, per the prompt rules). This ensures the user always gets a human-readable explanation alongside any charts or tables. It aligns with the idea from Anthropic's examples that the assistant should explain results, not just produce structured data silently.

### Tool Selection and Usage Guidance:
* **Tool Selection and Usage Guidance:** We continue to allow Claude to **auto-select tools** as needed (`tool_choice: "auto"`), which is the recommended usage for letting the model decide the best tool for each subtask. Our prompts guide Claude on when to use which tool (e.g., "use `generate_graph_data` for charts, `...table_data` for tables, do not just describe data in text if a tool is available"). This nudging, combined with the structured turn-by-turn flow, maximizes the chance that Claude utilizes the tools appropriately and produces a rich answer. We also honor user instructions about tools: the system prompt explicitly says if the user requests specific tools or a certain number of metrics, Claude **must** fulfill that by using the tools accordingly. The multi-turn approach will faithfully carry out each such request (e.g. if user asks for two metrics, Claude will issue two `generate_financial_metric` calls, and our loop will capture both).

In summary, the new implementation plan introduces a clean separation of concerns and a robust multi-step interaction model. Each analysis type can have a tailored strategy (with its own system prompt and flow), and ClaudeService provides a simple interface for each turn's API call and result processing. This design not only resolves the current shortcomings (ensuring all charts/tables are generated and analysis is on-point for the query), but also makes the system easier to extend. Future analysis types or tool updates can be integrated by adding new strategies or tools without breaking existing flows. By aligning closely with Anthropic's tool usage patterns and using the Strategy pattern for modularity, we achieve a solution that is both **token-efficient and reliable** in producing comprehensive financial analysis results with multiple visualization artifacts. (All these changes will be implemented alongside updates to unit tests and documentation to ensure a smooth transition to the new orchestration mechanism.)

**MVP–Focused Audit Framework (Integration & Data-Flow Emphasis)**
*(Python FastAPI backend + TS/JS frontend; security / accessibility deferred.)*
**Audit Target:** the new multi-turn orchestration for `analysisType=comprehensive_tools` (Strategy pattern, Claude tool loop, updated router).

---

### 1. Charter & Scope

| Item             | Notes                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Objective**    | Verify the *end-to-end* path that creates a comprehensive analysis with multiple charts/metrics, stores it, and renders it in the UI—using the new Strategy classes and `ClaudeService.execute_tool_interaction_turn`.                                                                                                                                                                                                        |
| **In Scope**     | <ul><li>FastAPI endpoint `POST /api/analysis/run`</li><li>Router → Strategy delegation (`analysis_service.py`)</li><li>`ComprehensiveAnalysisStrategy` loop & helper utilities</li><li>`ClaudeService` tool-turn helper</li><li>Pydantic tool schemas & JSON validation</li><li>Frontend store / Canvas component that displays `visualizations.charts`, `tables`, `metrics`</li><li>CI tests covering the new flow</li></ul> |
| **Out of Scope** | Auth, rate-limit rules, advanced caching, non-comprehensive analysis modes.                                                                                                                                                                                                                                                                                                                                                   |

---

### 2. Repo Structure (Integration Hot-Spots)

```
/backend/
  services/
    analysis_service.py          # NEW router→strategy map
    analysis_strategies/
      base_strategy.py
      comprehensive_strategy.py  # multi-turn orchestration
  pdf_processing/
    claude_service.py            # execute_tool_interaction_turn()
  models/
    tools.py                     # ALL_TOOLS_DICT, Pydantic schemas
  routers/
    analysis.py                  # /api/analysis/run
  tests/
    integration/
      test_comprehensive_flow.py
/frontend/
  src/
    api/analysisApi.ts           # POST /analysis/run
    stores/analysisStore.ts      # holds analysis result
    components/AnalysisCanvas.tsx
  tests/e2e/comprehensive.spec.ts
.github/workflows/ci.yml
```

---

### 3. Pillar: Integration & Data-Flow Checks

| Aspect                        | Current State                                                                  | Risk / Gap                                                     | Recommended Action                                              |
| ----------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------- | --------------------------------------------------------------- |
| **A. Router → Strategy**      | `analysis_service.run_analysis` now imports `strategy_map` and delegates.      | Missing guard if `analysis_type` not found → 500 error.        | Return 400 w/ list of valid types. Add unit test.               |
| **B. Claude Turn Helper**     | `execute_tool_interaction_turn` wraps `client.messages.create`.                | No retry/back-off on Claude 5xx; missing timeout param.        | Add `try/except` w/ exponential back-off, `timeout=60`.         |
| **C. Tool Schema Validation** | `_process_visualization_input` validates JSON vs Pydantic.                     | If schema fails, strategy continues silently (logs only).      | Raise `ValueError`; map to 422 API response.                    |
| **D. Result Consolidation**   | Strategy returns `{"visualizations":{"charts":[],"tables":[]}, "metrics":[]}`. | Frontend expects `charts` & `tables` at root for legacy flows. | Update TS typegen & Canvas parser OR add backwards-compat shim. |
| **E. Database Persist**       | `AnalysisRepository.save_result` unchanged.                                    | New volume of chart objects may exceed text column size.       | Switch `charts`/`tables` to JSONB in Postgres.                  |
| **F. Frontend Canvas**        | Renders charts from `visualizations.charts`.                                   | No defensive check if chart array empty → crash.               | Add graceful "No visuals generated" fallback.                   |
| **G. CI Pipeline**            | Unit tests for strategy; e2e covers happy path.                                | No test for Claude error injection.                            | Add mocked 5xx test to ensure retry logic.                      |

---

### 4. Manual Integration Sanity Checks

1. **Happy Path**

   * Run `POST /api/analysis/run` with `analysis_type="comprehensive_tools"` and a small PDF.
   * Confirm **7-turn max** interaction finishes with ≥ 1 chart + ≤ 500 tokens of text.

2. **Schema Break**

   * Tamper with tool JSON (omit required field) → expect 422 from backend and user-friendly alert in UI.

3. **Large Payload**

   * Use a doc generating 10+ charts; reload Canvas → ensure no layout shift and DB row persists (check JSONB).

---

### 5. Findings Backlog & Priority

| Priority    | Finding                                          | Owner    |
| ----------- | ------------------------------------------------ | -------- |
| **Blocker** | Router returns 500 on invalid `analysis_type`.   | Backend  |
| **High**    | UI crash on empty `visualizations.charts`.       | Frontend |
| **High**    | No DB migration to JSONB for large chart arrays. | DBA      |
| **Medium**  | Lack of retry logic for Claude 5xx errors.       | Backend  |
| **Low**     | Missing API docs for new response envelope.      | Docs     |

---

### 6. CI/CD Integration Steps (Incremental)

```yaml
jobs:
  contract-check:
    steps:
      - Generate OpenAPI spec → compare
      - openapi-generator typescript-axios > src/models
  backend-tests:
    steps:
      - pytest -m "unit or integration"
      - pytest tests/integration/test_comprehensive_flow.py
  e2e:
    steps:
      - docker-compose up -d
      - pnpm playwright test e2e/comprehensive.spec.ts
```

*Gate = fail on schema diff, failing tests, or Claude mock errors.*

---

### 7. Remediation Roadmap

| Day          | Task                                                                           |
| ------------ | ------------------------------------------------------------------------------ |
| **Day 0–1**  | Add type-not-found guard + 400 response; UI empty-chart fallback.              |
| **Sprint 1** | DB migration (`charts`, `tables` JSONB); Claude retry logic; update TS models. |
| **Post-MVP** | Pact contract tests; richer error surface to UX; pagination of visualizations. |

---

#### MVP Deliverables

* Router delegates cleanly; 400 on bad type
* Strategy loop reliably produces multi-chart result
* DB schema updated for chart payloads
* Frontend Canvas renders or gracefully degrades
* CI gates for contract, unit, integration, e2e paths

This audit ensures the new multi-turn, multi-tool analysis path is rock-solid and production-ready for MVP launch.
