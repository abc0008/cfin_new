# FDAS (Financial Document Analysis System) Backend

This is the backend server for the Financial Document Analysis System, providing API endpoints for document upload, processing, and analysis using Claude API's native PDF capabilities, LangChain, and LangGraph.

## Features

- Direct PDF document processing via Claude API (no preprocessing required)
- Native citation extraction and linking
- Automatic financial data recognition and extraction
- Support for complex financial document structures
- Fallback OCR processing (only if needed)
- Conversation management with document context
- Financial analysis and visualization

## Requirements

- Python 3.9+
- FastAPI
- SQLAlchemy
- Anthropic Claude API access (claude-3-sonnet-latest or higher)
- LangChain and LangGraph

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the backend directory with the following variables:

```
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-3-sonnet-latest

# Database Configuration
DATABASE_URL=sqlite:///./fdas.db  # For development; use PostgreSQL in production

# Storage Configuration
UPLOAD_DIR=./uploads
STORAGE_TYPE=local  # Options: local, s3

# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=True
```

### 3. Run the server

```bash
python run.py
```

The server will start on `http://localhost:8000` by default.

## API Endpoints

### Documents

- `POST /api/documents/upload` - Upload a financial document
- `GET /api/documents/{document_id}` - Get document details
- `GET /api/documents` - List user documents
- `GET /api/documents/{document_id}/citations` - Get document citations
- `GET /api/documents/{document_id}/citations/{citation_id}` - Get citation details
- `DELETE /api/documents/{document_id}` - Delete a document

### Conversation

- `POST /api/conversation/message` - Send a message
- `GET /api/conversation/{conversation_id}` - Get conversation history
- `POST /api/conversation/create` - Create a new conversation
- `GET /api/conversation` - List user conversations

### Analysis

- `POST /api/analysis/run` - Run analysis on a document
- `GET /api/analysis/{analysis_id}` - Get analysis results

## Architecture

The backend is built with the following components:

1. **FastAPI Application** - Provides RESTful API endpoints and handles requests
2. **Document Service** - Manages document upload, storage, and processing
3. **Claude Service** - Interacts with Claude API for document analysis
4. **LangChain/LangGraph Service** - Orchestrates AI workflows and enhances document processing
5. **Database Models** - SQLAlchemy ORM models for persistent data storage
6. **Storage Service** - Manages file storage (local filesystem or S3)

## Development

### Database Migrations

The application uses SQLAlchemy for database management. If you need to make changes to the database schema:

1. Update the models in `models/database_models.py`
2. Run database initialization:

```bash
python -c "from utils.init_db import run_init_db; run_init_db()"
```

### Testing

Run tests with pytest:

```bash
pytest
```

## Production Deployment

For production deployment:

1. Use a production-grade database (PostgreSQL recommended)
2. Set up proper authentication (OAuth, API keys)
3. Configure CORS for your specific frontend domain
4. Use HTTPS for secure communication
5. Consider Docker containerization for easier deployment


## Adding a new Analysis Strategy

This guide outlines how to add a new analysis strategy to the cfin backend, allowing for modular and maintainable expansion of analysis capabilities. Each strategy encapsulates the logic for a specific type of analysis, including prompt engineering and interaction with the Claude language model.

### 1. Define the Strategy Class

Create a new Python file in the `cfin/backend/services/analysis_strategies/` directory (e.g., `my_new_strategy.py`). Inside this file, define a class that inherits from `AnalysisStrategy` (defined in `base_strategy.py`).

```python
# cfin/backend/services/analysis_strategies/my_new_strategy.py
import logging
from typing import Dict, Any, List

from .base_strategy import AnalysisStrategy
from pdf_processing.claude_service import ClaudeService
from models.database_models import Document

logger = logging.getLogger(__name__)

# Define a system prompt tailored for this new strategy
MY_NEW_STRATEGY_SYSTEM_PROMPT = """
[Your detailed system prompt here. Explain the AI's role, the task, and expected output format.]
Remember to use Tool Choreography if specific tool sequences are needed.
"""

class MyNewStrategy(AnalysisStrategy):
    def __init__(self, claude_service: ClaudeService):
        super().__init__(claude_service)
        self.system_prompt = MY_NEW_STRATEGY_SYSTEM_PROMPT

    async def execute(
        self,
        aggregated_text: str,
        documents: List[Document],
        parameters: Dict[str, Any],
        user_query: str,
        # Optionally, add analysis_id if needed for progress updates
        # analysis_id: str 
    ) -> Dict[str, Any]:
        logger.info(f"Executing MyNewStrategy for query: {user_query}")
        messages = [
            {"role": "user", "content": f"{user_query}\n\nDocument Context:\n{aggregated_text}"}
        ]
        
        accumulated_text = ""
        accumulated_charts = []
        accumulated_tables = []
        accumulated_metrics = []
        
        # Max 7 turns, similar to other strategies
        for turn in range(7):
            logger.info(f"MyNewStrategy - Turn {turn + 1}")
            # Use the ClaudeService to interact with the model
            # The tools argument will default to CLAUDE_API_TOOLS_LIST from ClaudeService's init
            raw_response = await self.claude_service.execute_tool_interaction_turn(
                system_prompt=self.system_prompt,
                messages=messages,
                # tools=specific_tools_for_this_turn, # Optional: if different from default
                # max_tokens=..., 
                # temperature=...
            )

            if not raw_response or not raw_response.content:
                logger.warning("MyNewStrategy: Received empty response from Claude.")
                break # Or handle error appropriately

            assistant_response_text = ""
            tool_results_to_append = []

            for content_block in raw_response.content:
                if content_block.type == "text":
                    assistant_response_text += content_block.text
                elif content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id
                    logger.info(f"MyNewStrategy: Claude wants to use tool: {tool_name} with ID: {tool_use_id}")
                    
                    # Process the tool input using processors from ALL_TOOLS_DICT in ClaudeService
                    # (ClaudeService._process_tool_calls handles this via tool_schemas_map)
                    # For direct simulation or if handling outside ClaudeService's built-in processing:
                    # processed_tool_output = self.claude_service.tool_schemas_map[tool_name].processor(tool_input)
                    # For now, we assume ClaudeService's _process_tool_calls will handle this internally if called.
                    # The execute_tool_interaction_turn itself doesn't process, it just returns raw response.
                    # The strategy must invoke the processing using the returned tool_use blocks.

                    # Example of how a strategy might directly use the processor if needed:
                    tool_schema = self.claude_service.tool_schemas_map.get(tool_name)
                    processed_output = None
                    if tool_schema and tool_schema.processor:
                        try:
                            processed_output = tool_schema.processor(tool_input)
                            logger.info(f"MyNewStrategy: Processed output for {tool_name}: {type(processed_output)}")
                        except Exception as e:
                            logger.error(f"MyNewStrategy: Error processing tool {tool_name}: {e}")
                            processed_output = {"error": str(e), "details": "Failed to process tool input."}
                    else:
                        logger.warning(f"MyNewStrategy: No processor found for tool {tool_name}")
                        processed_output = {"error": "Tool not supported or no processor defined."}

                    tool_results_to_append.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(processed_output) if not isinstance(processed_output, str) else processed_output,
                        # Add is_error key if your tool result schema supports it
                        # "is_error": isinstance(processed_output, dict) and "error" in processed_output
                    })

                    # Accumulate based on tool type and processed_output structure
                    # This mirrors logic in comprehensive_strategy.py
                    if tool_name == "generate_graph_data" and processed_output and not (isinstance(processed_output, dict) and "error" in processed_output):
                        accumulated_charts.append(processed_output)
                    elif tool_name == "generate_table_data" and processed_output and not (isinstance(processed_output, dict) and "error" in processed_output):
                        accumulated_tables.append(processed_output)
                    elif tool_name == "generate_financial_metric" and processed_output and not (isinstance(processed_output, dict) and "error" in processed_output):
                        accumulated_metrics.append(processed_output)
            
            if assistant_response_text:
                accumulated_text += (("\n\n" if accumulated_text else "") + f"Turn {turn + 1}:\n" + assistant_response_text)
                messages.append({"role": "assistant", "content": assistant_response_text}) # or pass raw_response.content blocks
            
            if tool_results_to_append:
                messages.append({"role": "user", "content": tool_results_to_append})
            
            if raw_response.stop_reason == "stop_sequence":
                logger.info("MyNewStrategy: Claude indicated stop_sequence.")
                break
            elif raw_response.stop_reason == "tool_use" and not tool_results_to_append:
                logger.warning("MyNewStrategy: stop_reason tool_use but no tools were processed to send back. Breaking.")
                break # Avoid deadloop if tool processing fails to yield a result to send back
        else: # Max turns reached
             logger.warning(f"MyNewStrategy: Max turns ({len(range(7))}) reached.")

        return {
            "analysis_text": accumulated_text.strip(),
            "visualizations": {
                "charts": [chart for chart in accumulated_charts if chart is not None],
                "tables": [table for table in accumulated_tables if table is not None]
            },
            "metrics": [metric for metric in accumulated_metrics if metric is not None]
        }

```

### 2. Register the Strategy

Open `cfin/backend/services/analysis_strategies/__init__.py` and add your new strategy to the `strategy_map`.

```python
# cfin/backend/services/analysis_strategies/__init__.py
from .base_strategy import AnalysisStrategy
from .comprehensive_strategy import ComprehensiveAnalysisStrategy
from .financial_template_strategy import FinancialTemplateStrategy
from .my_new_strategy import MyNewStrategy # <-- Import your new strategy

strategy_map: Dict[str, type[AnalysisStrategy]] = {
    "comprehensive_tools": ComprehensiveAnalysisStrategy,
    "financial_template": FinancialTemplateStrategy,
    "my_new_analysis_type": MyNewStrategy, # <-- Add your strategy here
}
```
Replace `"my_new_analysis_type"` with the string identifier that will be used in API requests to trigger this strategy.

### 3. Define Tools and Processors (If new tools are needed)

If your new strategy requires tools not already defined, or existing tools need different processing logic for this strategy:

*   **Tool Schemas**: Define or update tool schemas in `cfin/backend/models/tools.py`. Each tool needs a name, description, and an `input_schema` (JSON schema).
*   **Tool Processors**: Implement the Python functions that execute the tool's logic (e.g., generating data for a chart, fetching external information) in `cfin/backend/utils/tool_processing.py`.
*   **Link Processor to Schema**: In `models/tools.py`, ensure your `ToolSchema` instance for the tool has its `processor` attribute pointing to the corresponding function from `tool_processing.py`. The `ALL_TOOLS_DICT` is used by `ClaudeService` to find these processors.

Your strategy's `execute` method (or the underlying `ClaudeService` calls) will then be able to invoke these tools and their processors.

### 4. Test Your Strategy

Create unit tests for your new strategy in `cfin/backend/tests/unit/strategies/` (e.g., `test_my_new_strategy.py`).

*   Mock `ClaudeService` and its `execute_tool_interaction_turn` method to simulate different responses from Claude (text, tool calls, errors).
*   If your strategy uses specific tool processors, you might mock `tool_processing.py` functions or the `processor` call itself to control their output during tests.
*   Assert that your strategy's `execute` method correctly processes Claude's responses, accumulates data (text, charts, tables, metrics), and returns the output in the standard `Dict[str, Any]` format.

### Prompt Engineering Best Practices for Strategies

Effective prompt engineering is crucial for getting reliable and accurate results from Claude, especially when using tools.

*   **Be Specific and Clear**: Clearly define the AI's role, the context, the task, and the expected output format. Avoid ambiguity.
*   **Persona**: Assigning a persona (e.g., "You are a Senior Financial Analyst for a regional bank") can help Claude adopt the desired tone and focus.
*   **Structured Output**: If you need the output in a specific structure (e.g., sections for "Key Findings", "Risks", "Recommendations"), explicitly state this in the prompt. Using XML tags or Markdown headings can help Claude structure its response.
*   **Tool Usage Guidance**: Clearly instruct Claude on when and how to use the available tools. Don't just list tools; explain their purpose.
    *   Example: "If you need to present time-series data, use the `generate_graph_data` tool with a 'line' chartType. For categorical comparisons, use a 'bar' chartType."
*   **Iterative Refinement**: Test your prompts with various inputs and observe Claude's behavior. Refine the prompt based on the results. Small changes in wording can have significant impacts.
*   **Temperature and Max Tokens**: For strategies requiring deterministic output or adherence to strict instructions, use a lower `temperature` (e.g., 0.0 to 0.3). Adjust `max_tokens` per turn to allow enough space for Claude's response without being excessive.

#### Tool Choreography

For complex analyses requiring a sequence of tool calls or specific tool combinations, employ **Tool Choreography**. This involves explicitly instructing Claude in the system prompt about the exact sequence and number of tool invocations.

*   **Enumerated Steps**: Break down the analysis into a series of imperative steps. Number them clearly.
    *   Example: 
        ```
        To complete this analysis, follow these steps precisely:
        1. Call the `generate_financial_metric` tool to calculate 'Total Revenue' for the last fiscal year.
        2. Call the `generate_financial_metric` tool again to calculate 'Net Profit Margin' for the same period.
        3. Using the results from step 1 and 2, call the `generate_table_data` tool to create a summary table with these two metrics.
        4. Provide a brief textual summary of these findings.
        Do not deviate from this sequence or number of tool calls.
        ```
*   **Specify Tool Count**: "Call `generate_financial_metric` exactly twice." or "Generate three distinct charts using `generate_graph_data`."
*   **Conditional Logic (Carefully)**: While direct programming logic is not Claude's forte, you can guide conditional-like behavior. "If 'Total Assets' are above $10M, then call `generate_anomaly_report_tool`. Otherwise, proceed to the next step." (Note: This relies on Claude's interpretation and might be less reliable than explicit sequences).
*   **Mandate Tool Use**: "You MUST use the `generate_graph_data` tool to visualize this trend; do not describe it only in text."

Tool Choreography reduces ambiguity and gives you more control over the analysis process, making tool usage more deterministic and aligned with your intended workflow. It's particularly useful for strategies that need to produce a consistent set of artifacts.

By following these steps and best practices, you can effectively extend the cfin application with new, powerful analysis capabilities. 