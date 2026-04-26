# CFIN / FDAS — Claude Managed Agents Templates

> Adapted from the official Anthropic Managed Agents cookbooks for
> the **Financial Document Analysis System (FDAS)**.
>
> These templates wire Claude Managed Agents to your existing
> architecture: **PDF viewer → on-PDF citations → chart panel → narrative**.

---

## Table of Contents

1. [Architecture Mapping](#1-architecture-mapping)
2. [Agent Definition (YAML / JSON / Python)](#2-agent-definition)
3. [Skills — Financial Analysis Conventions](#3-skills)
4. [Quickstart — First FDAS Session](#4-quickstart)
5. [Data Analyst — Full Analysis Pipeline](#5-data-analyst-pipeline)
6. [Prompt Versioning & Rollback](#6-prompt-versioning)
7. [Iterate — Fix Failing Citations](#7-iterate)
8. [Human-in-the-Loop — Narrative Review Gate](#8-human-in-the-loop)
9. [Production Setup — Webhooks & Vaults](#9-production-setup)
10. [Custom Tools Reference](#10-custom-tools-reference)

---

## 1. Architecture Mapping

Your FDAS today:

```
Next.js  ──REST/WS──▶  FastAPI  ──▶  Claude API / LangGraph
  │                       │
  ├─ PDFViewer            ├─ pdf_processing/
  ├─ Canvas (Recharts)    ├─ services/analysis_strategies/
  ├─ CitationContext       ├─ models/tools.py
  └─ StreamingChat        └─ routes/websocket.py
```

With Managed Agents, the FastAPI backend's Claude orchestration moves
into Anthropic's hosted runtime. Your Next.js frontend talks to
Managed Agents sessions instead of (or alongside) your backend:

```
Next.js  ──▶  Anthropic Managed Agents API
                 │
                 ├─ Agent (model + system prompt + tools + skills)
                 ├─ Environment (packages: pandas, plotly, pymupdf)
                 ├─ Session (mounted PDF files, event stream)
                 │    ├─ Built-in tools: bash, read, write, edit, grep
                 │    ├─ Custom tools: generate_chart, extract_citations,
                 │    │                submit_narrative, request_review
                 │    └─ MCP toolsets: (optional) Supabase, external APIs
                 └─ Files API (upload PDFs, download reports)
```

### Concept mapping

| FDAS Concept | Managed Agents Equivalent |
|---|---|
| `POST /api/documents/upload` | `client.beta.files.upload()` → mount as resource |
| `POST /api/analysis/run` | Send `user.message` event to session |
| `analysis_blocks` (chart/table/metric) | Custom tool `generate_chart` / `generate_table` / `generate_metric` |
| `Citation` with `rects`, `highlightId` | Custom tool `extract_citations` returns citation payloads |
| `analysisText` / narrative | Agent `agent.message` text events with citation markers |
| WebSocket streaming | SSE event stream (`sessions.events.stream`) |
| `ConversationService` | Session (multi-turn, stateful) |
| `AnalysisStrategy` prebuilt prompts | Skills (uploaded once, referenced by ID) |

---

## 2. Agent Definition

### YAML

```yaml
name: FDAS Financial Document Analyst
description: >-
  Analyze financial PDFs, extract data, generate charts with citations,
  and produce narrative reports with on-PDF source references.
model: claude-sonnet-4-6
system: >-
  You are a senior financial analyst working inside the FDAS platform.
  Users upload financial documents (10-Ks, annual reports, earnings
  transcripts, CIMs) and ask questions. Your job is to analyze the
  document, produce structured visualizations, cite your sources with
  precise PDF locations, and write a clear narrative.


  WORKFLOW


  1. Inspect the document. Read the mounted PDF. Print a summary of
  what the document contains: company name, document type, reporting
  period, page count. Always look before you compute.

  2. Extract financial data. Use Python (pandas) to structure the
  key financial data: revenue, expenses, margins, ratios, segment
  breakdowns. Save intermediate CSVs to /mnt/session/outputs/.

  3. Generate visualizations. Call generate_chart for each insight
  worth visualizing. Prefer bar charts for comparisons, line charts
  for trends, pie charts for composition, tables for detailed
  breakdowns. Each chart must include a title, axis labels, and the
  data series. Use the block_type values: chart, table, metric.

  4. Extract citations. For every claim backed by the document, call
  extract_citations with the cited text and page number. The platform
  will resolve the exact rects for PDF highlighting. Citations link
  your narrative to the source material.

  5. Write the narrative. Produce a structured analysis with an
  executive summary (2-3 sentences), key metrics (call generate_metric
  for each headline number), detailed findings with inline citation
  references [cite:N], risks and caveats, and actionable
  recommendations.

  6. Save outputs. Write the final report to
  /mnt/session/outputs/report.html. Confirm Saved: report.html
  when done.


  STYLE

  Professional and precise. Let the data speak with concrete numbers.
  Short paragraphs (2-3 sentences) between charts. Always cite the
  page and section when referencing a specific figure. Default to
  simple, readable analysis over clever one-liners.


  CHART FORMAT

  Return chart data as JSON: block_type=chart, chart_type is one of
  bar/line/pie/area/scatter, title string, config with xAxisKey, and
  a data array of objects.


  CITATION FORMAT

  When citing, reference by [cite:N] in narrative text. Each citation
  maps to an extract_citations call that returns id, page, and rects.


  METRIC FORMAT

  block_type=metric, name string, value string, optional change and
  period strings.
tools:
  - type: agent_toolset_20260401
    default_config:
      enabled: true
      permission_policy:
        type: always_allow
    configs:
      - name: web_search
        enabled: false
      - name: web_fetch
        enabled: false
  - type: custom
    name: generate_chart
    description: >-
      Generate a chart visualization block for the FDAS frontend.
      Returns the chart block with an assigned ID.
    input_schema:
      type: object
      properties:
        block_type:
          type: string
          enum:
            - chart
        chart_type:
          type: string
          enum:
            - bar
            - multiBar
            - line
            - pie
            - area
            - stackedArea
            - scatter
        title:
          type: string
        config:
          type: object
          properties:
            xAxisKey:
              type: string
          required:
            - xAxisKey
        data:
          type: array
          items:
            type: object
      required:
        - block_type
        - chart_type
        - title
        - config
        - data
  - type: custom
    name: generate_table
    description: >-
      Generate a table visualization block for the FDAS frontend.
    input_schema:
      type: object
      properties:
        block_type:
          type: string
          enum:
            - table
        title:
          type: string
        columns:
          type: array
          items:
            type: object
            properties:
              key:
                type: string
              label:
                type: string
            required:
              - key
              - label
        data:
          type: array
          items:
            type: object
      required:
        - block_type
        - title
        - columns
        - data
  - type: custom
    name: generate_metric
    description: >-
      Generate a metric card for the FDAS frontend dashboard.
    input_schema:
      type: object
      properties:
        block_type:
          type: string
          enum:
            - metric
        name:
          type: string
        value:
          type: string
        change:
          type: string
        period:
          type: string
      required:
        - block_type
        - name
        - value
  - type: custom
    name: extract_citations
    description: >-
      Extract a citation from the PDF document. Returns citation ID,
      highlight rects, and page location for the FDAS PDF viewer overlay.
    input_schema:
      type: object
      properties:
        document_id:
          type: string
        cited_text:
          type: string
          description: The exact text being cited from the document.
        page_number:
          type: integer
        display_text:
          type: string
          description: >-
            Processed text to show users, for example
            Interest Income 900.0M.
      required:
        - document_id
        - cited_text
        - page_number
  - type: custom
    name: request_review
    description: >-
      Submit the completed analysis for human review before publishing.
      The session pauses until the reviewer approves or requests changes.
    input_schema:
      type: object
      properties:
        summary:
          type: string
          description: Brief summary of the analysis for the reviewer.
        report_path:
          type: string
          description: Path to the generated report file.
      required:
        - summary
metadata:
  template: fdas-financial-analyst
```

### JSON

```json
{
  "name": "FDAS Financial Document Analyst",
  "description": "Analyze financial PDFs — extract data, generate charts with citations, and produce narrative reports with on-PDF source references.",
  "model": "claude-sonnet-4-6",
  "system": "You are a senior financial analyst working inside the FDAS platform.\nUsers upload financial documents (10-Ks, annual reports, earnings\ntranscripts, CIMs) and ask questions. Your job is to analyze the\ndocument, produce structured visualizations, cite your sources with\nprecise PDF locations, and write a clear narrative.\n\n## Workflow\n\n1. **Inspect the document.** Read the mounted PDF. Print a summary of\n   what the document contains: company name, document type, reporting\n   period, page count. Always look before you compute.\n\n2. **Extract financial data.** Use Python (pandas) to structure the\n   key financial data: revenue, expenses, margins, ratios, segment\n   breakdowns. Save intermediate CSVs to /mnt/session/outputs/.\n\n3. **Generate visualizations.** Call generate_chart for each insight\n   worth visualizing. Prefer:\n   - Bar charts for comparisons (revenue by segment, YoY growth)\n   - Line charts for trends (quarterly revenue, margin trajectory)\n   - Pie charts for composition (revenue mix, expense breakdown)\n   - Tables for detailed breakdowns (balance sheet, cash flow)\n   Each chart must include a title, axis labels, and the data series.\n   Use the block_type values: \"chart\", \"table\", \"metric\".\n\n4. **Extract citations.** For every claim backed by the document, call\n   extract_citations with the cited text and page number. The platform\n   will resolve the exact rects for PDF highlighting. Citations link\n   your narrative to the source material.\n\n5. **Write the narrative.** Produce a structured analysis with:\n   - Executive summary (2-3 sentences, lead with the most actionable finding)\n   - Key metrics (call generate_metric for each headline number)\n   - Detailed findings with inline citation references [cite:N]\n   - Risks and caveats (sample size, restatements, one-time items)\n   - Actionable recommendations\n\n6. **Save outputs.** Write the final report to /mnt/session/outputs/report.html.\n   Confirm \"Saved: report.html\" when done.\n\n## Style\n- Professional and precise. Let the data speak with concrete numbers.\n- Short paragraphs (2-3 sentences) between charts.\n- Always cite the page and section when referencing a specific figure.\n- Default to simple, readable analysis over clever one-liners.\n\n## Chart Format\nReturn chart data as JSON matching this schema:\n{\"block_type\": \"chart\", \"chart_type\": \"bar\", \"title\": \"...\", \"config\": {\"xAxisKey\": \"...\"}, \"data\": [...]}\n\n## Metric Format\n{\"block_type\": \"metric\", \"name\": \"...\", \"value\": \"...\", \"change\": \"...\", \"period\": \"...\"}\n\n## Citation Format\nWhen citing, reference by [cite:N] in narrative text.",
  "tools": [
    {
      "type": "agent_toolset_20260401",
      "default_config": {
        "enabled": true,
        "permission_policy": { "type": "always_allow" }
      },
      "configs": [
        { "name": "web_search", "enabled": false },
        { "name": "web_fetch", "enabled": false }
      ]
    },
    {
      "type": "custom",
      "name": "generate_chart",
      "description": "Generate a chart visualization block for the FDAS frontend.",
      "input_schema": {
        "type": "object",
        "properties": {
          "block_type": { "type": "string", "enum": ["chart"] },
          "chart_type": { "type": "string", "enum": ["bar", "multiBar", "line", "pie", "area", "stackedArea", "scatter"] },
          "title": { "type": "string" },
          "config": {
            "type": "object",
            "properties": { "xAxisKey": { "type": "string" } },
            "required": ["xAxisKey"]
          },
          "data": { "type": "array", "items": { "type": "object" } }
        },
        "required": ["block_type", "chart_type", "title", "config", "data"]
      }
    },
    {
      "type": "custom",
      "name": "generate_table",
      "description": "Generate a table visualization block for the FDAS frontend.",
      "input_schema": {
        "type": "object",
        "properties": {
          "block_type": { "type": "string", "enum": ["table"] },
          "title": { "type": "string" },
          "columns": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": { "key": { "type": "string" }, "label": { "type": "string" } },
              "required": ["key", "label"]
            }
          },
          "data": { "type": "array", "items": { "type": "object" } }
        },
        "required": ["block_type", "title", "columns", "data"]
      }
    },
    {
      "type": "custom",
      "name": "generate_metric",
      "description": "Generate a metric card for the FDAS frontend dashboard.",
      "input_schema": {
        "type": "object",
        "properties": {
          "block_type": { "type": "string", "enum": ["metric"] },
          "name": { "type": "string" },
          "value": { "type": "string" },
          "change": { "type": "string" },
          "period": { "type": "string" }
        },
        "required": ["block_type", "name", "value"]
      }
    },
    {
      "type": "custom",
      "name": "extract_citations",
      "description": "Extract a citation from the PDF document. Returns citation ID, highlight rects, and page location for the FDAS PDF viewer overlay.",
      "input_schema": {
        "type": "object",
        "properties": {
          "document_id": { "type": "string" },
          "cited_text": { "type": "string", "description": "The exact text being cited from the document." },
          "page_number": { "type": "integer" },
          "display_text": { "type": "string", "description": "Processed text to show users." }
        },
        "required": ["document_id", "cited_text", "page_number"]
      }
    },
    {
      "type": "custom",
      "name": "request_review",
      "description": "Submit the completed analysis for human review before publishing.",
      "input_schema": {
        "type": "object",
        "properties": {
          "summary": { "type": "string" },
          "report_path": { "type": "string" }
        },
        "required": ["summary"]
      }
    }
  ],
  "metadata": {
    "template": "fdas-financial-analyst"
  }
}
```

### Python — Full Session Setup

```python
from anthropic import Anthropic
from pathlib import Path
import json

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ── 1. Create the agent ─────────────────────────────────────────

FDAS_SYSTEM_PROMPT = """\
You are a senior financial analyst working inside the FDAS platform.
Users upload financial documents (10-Ks, annual reports, earnings
transcripts, CIMs) and ask questions. Your job is to analyze the
document, produce structured visualizations, cite your sources with
precise PDF locations, and write a clear narrative.

## Workflow

1. **Inspect the document.** Read the mounted PDF. Print a summary of
   what the document contains: company name, document type, reporting
   period, page count. Always look before you compute.

2. **Extract financial data.** Use Python (pandas) to structure the
   key financial data: revenue, expenses, margins, ratios, segment
   breakdowns. Save intermediate CSVs to /mnt/session/outputs/.

3. **Generate visualizations.** Call generate_chart for each insight
   worth visualizing. Prefer:
   - Bar charts for comparisons (revenue by segment, YoY growth)
   - Line charts for trends (quarterly revenue, margin trajectory)
   - Pie charts for composition (revenue mix, expense breakdown)
   - Tables for detailed breakdowns (balance sheet, cash flow)
   Each chart must include a title, axis labels, and the data series.

4. **Extract citations.** For every claim backed by the document, call
   extract_citations with the cited text and page number.

5. **Write the narrative.** Produce a structured analysis with:
   - Executive summary (2-3 sentences)
   - Key metrics (call generate_metric for each headline number)
   - Detailed findings with inline citation references [cite:N]
   - Risks and caveats
   - Actionable recommendations

6. **Save outputs.** Write the final report to
   /mnt/session/outputs/report.html and confirm.

## Style
- Professional and precise. Concrete numbers, short paragraphs.
- Always cite page and section for specific figures.

## Chart Data Format
{"block_type": "chart", "chart_type": "bar", "title": "...",
 "config": {"xAxisKey": "..."}, "data": [...]}

## Metric Data Format
{"block_type": "metric", "name": "...", "value": "...",
 "change": "...", "period": "..."}
"""

agent = client.beta.agents.create(
    name="fdas-financial-analyst",
    model=MODEL,
    system=FDAS_SYSTEM_PROMPT,
    tools=[
        {
            "type": "agent_toolset_20260401",
            "default_config": {
                "enabled": True,
                "permission_policy": {"type": "always_allow"},
            },
            "configs": [
                {"name": "web_search", "enabled": False},
                {"name": "web_fetch", "enabled": False},
            ],
        },
        {
            "type": "custom",
            "name": "generate_chart",
            "description": (
                "Generate a chart visualization block for the FDAS frontend. "
                "Returns the chart block with an assigned ID."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "block_type": {"type": "string", "enum": ["chart"]},
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "multiBar", "line", "pie",
                                 "area", "stackedArea", "scatter"],
                    },
                    "title": {"type": "string"},
                    "config": {
                        "type": "object",
                        "properties": {"xAxisKey": {"type": "string"}},
                        "required": ["xAxisKey"],
                    },
                    "data": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["block_type", "chart_type", "title",
                             "config", "data"],
            },
        },
        {
            "type": "custom",
            "name": "generate_table",
            "description": "Generate a table visualization block.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "block_type": {"type": "string", "enum": ["table"]},
                    "title": {"type": "string"},
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["key", "label"],
                        },
                    },
                    "data": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["block_type", "title", "columns", "data"],
            },
        },
        {
            "type": "custom",
            "name": "generate_metric",
            "description": "Generate a metric card for the FDAS dashboard.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "block_type": {"type": "string", "enum": ["metric"]},
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "change": {"type": "string"},
                    "period": {"type": "string"},
                },
                "required": ["block_type", "name", "value"],
            },
        },
        {
            "type": "custom",
            "name": "extract_citations",
            "description": (
                "Extract a citation from the PDF. Returns citation ID, "
                "highlight rects, and page location for the PDF viewer."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "cited_text": {"type": "string"},
                    "page_number": {"type": "integer"},
                    "display_text": {"type": "string"},
                },
                "required": ["document_id", "cited_text", "page_number"],
            },
        },
        {
            "type": "custom",
            "name": "request_review",
            "description": (
                "Submit the analysis for human review before publishing."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "report_path": {"type": "string"},
                },
                "required": ["summary"],
            },
        },
    ],
)

AGENT_ID = agent.id
AGENT_VERSION = agent.version
print(f"Agent: {AGENT_ID} v{AGENT_VERSION}")
```

---

## 3. Skills — Financial Analysis Conventions

Upload once, reference on every agent that needs financial analysis context.

```python
FINANCIAL_ANALYSIS_SKILL = """\
---
name: fdas-financial-analysis
description: Conventions for analyzing financial documents in the FDAS platform.
---

# Financial Document Analysis Conventions

## Document Types & What to Extract

### 10-K / Annual Report
- Income statement: revenue, COGS, gross margin, operating income, net income
- Balance sheet: total assets, liabilities, equity, cash position
- Cash flow statement: operating, investing, financing cash flows
- Key ratios: current ratio, debt-to-equity, ROE, ROA
- Segment breakdowns when available
- Management discussion & analysis highlights

### Earnings Transcript
- Reported vs consensus figures
- Forward guidance and revisions
- Management tone and confidence signals
- Analyst Q&A key themes

### CIM (Confidential Information Memorandum)
- Business overview and market position
- Historical and projected financials
- Key investment highlights and risks
- Comparable transactions if mentioned

## Chart Conventions

All charts must:
- Include xAxisKey in config matching a key in the data array
- Use descriptive titles ("Revenue by Segment, FY2024" not "Chart 1")
- Format monetary values with $ and appropriate scale (M, B)
- Format percentages with % suffix
- Use consistent color schemes across related charts

Preferred chart types by use case:
- Revenue/expense comparison → bar or multiBar
- Time series trends → line
- Composition/mix → pie (≤6 slices) or stackedArea
- Correlation → scatter
- Detailed numbers → table

## Citation Conventions

Every quantitative claim must have a citation. Citations must:
- Reference the exact text from the PDF (cited_text)
- Include the page number where the text appears
- Provide a human-readable display_text for the UI
- Be numbered sequentially [cite:1], [cite:2], etc.

## Narrative Structure

1. **Executive Summary** — 2-3 sentences, lead with the headline finding
2. **Key Metrics** — 3-5 headline numbers as metric cards
3. **Revenue Analysis** — trends, segments, drivers
4. **Profitability Analysis** — margins, operating leverage
5. **Balance Sheet & Cash Flow** — liquidity, capital structure
6. **Risks & Caveats** — one-time items, restatements, sample size
7. **Recommendations** — actionable next steps

## Analysis Strategies

Match the user's intent to the right depth:
- "Quick overview" → Key metrics + executive summary only
- "Comprehensive analysis" → Full narrative with all sections
- "Compare periods" → Focus on YoY/QoQ deltas
- "Specific question" → Targeted answer with supporting citations
"""

skill = client.beta.skills.create(
    display_title="fdas-financial-analysis",
    files=[
        ("fdas-financial-analysis/SKILL.md",
         FINANCIAL_ANALYSIS_SKILL.encode(),
         "text/markdown"),
    ],
)
print(f"Skill: {skill.id} (version {skill.latest_version})")
```

Attach the skill to the agent:

```python
agent = client.beta.agents.create(
    name="fdas-financial-analyst",
    model=MODEL,
    system=FDAS_SYSTEM_PROMPT,
    skills=[
        {"type": "custom", "skill_id": skill.id,
         "version": skill.latest_version},
    ],
    tools=[...],  # same tools as above
)
```

---

## 4. Quickstart — First FDAS Session

Adapted from the [Managed Agents Quickstart](https://platform.claude.com/docs/en/managed-agents/quickstart).

```python
# ── 1. Create environment with PDF/data packages ────────────────

env = client.beta.environments.create(
    name="fdas-analysis-env",
    config={
        "type": "cloud",
        "networking": {"type": "limited"},
        "packages": {
            "type": "packages",
            "pip": ["pandas", "plotly", "pymupdf", "openpyxl"],
        },
    },
)

# ── 2. Upload a financial PDF ───────────────────────────────────

pdf_path = Path("uploads/fidelity-10k-2024.pdf")
with pdf_path.open("rb") as f:
    pdf_file = client.beta.files.upload(
        file=(pdf_path.name, f, "application/pdf")
    )
print(f"Uploaded {pdf_path.name} ({pdf_file.size_bytes} bytes)")

# ── 3. Create a session with the PDF mounted ────────────────────

session = client.beta.sessions.create(
    environment_id=env.id,
    agent={"type": "agent", "id": AGENT_ID, "version": AGENT_VERSION},
    resources=[
        {"type": "file", "file_id": pdf_file.id,
         "mount_path": f"documents/{pdf_path.name}"},
    ],
    title=f"Analysis: {pdf_path.stem}",
)
print(f"Session: {session.id}")

# ── 4. Send the analysis request and stream ─────────────────────

ANALYSIS_PROMPT = f"""\
Analyze the financial document at /mnt/session/uploads/documents/{pdf_path.name}.

Focus on:
- Revenue and profitability trends
- Key financial ratios
- Segment performance
- Notable risks or red flags

Produce a comprehensive analysis with charts, citations, and narrative.
"""

# Custom tool handler
analysis_blocks = []
citations = []
citation_counter = 0


def handle_custom_tool(name: str, args: dict) -> dict:
    global citation_counter
    if name == "generate_chart":
        block_id = f"chart-{len(analysis_blocks)}"
        block = {"id": block_id, **args}
        analysis_blocks.append(block)
        return {"block_id": block_id, "status": "rendered"}

    if name == "generate_table":
        block_id = f"table-{len(analysis_blocks)}"
        block = {"id": block_id, **args}
        analysis_blocks.append(block)
        return {"block_id": block_id, "status": "rendered"}

    if name == "generate_metric":
        block_id = f"metric-{len(analysis_blocks)}"
        block = {"id": block_id, **args}
        analysis_blocks.append(block)
        return {"block_id": block_id, "status": "rendered"}

    if name == "extract_citations":
        citation_counter += 1
        cit_id = f"cite-{citation_counter}"
        citation = {
            "id": cit_id,
            "highlightId": cit_id,
            "documentId": args["document_id"],
            "citedText": args["cited_text"],
            "displayText": args.get("display_text", args["cited_text"]),
            "page_number": args["page_number"],
            "type": "page_location",
            "rects": [],  # Resolved by frontend PDF text search
        }
        citations.append(citation)
        return {"citation_id": cit_id, "citation_number": citation_counter}

    if name == "request_review":
        return {"status": "auto_approved", "reviewer": "system"}

    raise ValueError(f"Unknown tool: {name}")


# ── 5. Stream and handle events ─────────────────────────────────

seen = set()
custom_calls = {}

with client.beta.sessions.events.stream(session.id) as stream:
    client.beta.sessions.events.send(
        session.id,
        events=[{
            "type": "user.message",
            "content": [{"type": "text", "text": ANALYSIS_PROMPT}],
        }],
    )

    for ev in stream:
        if ev.id in seen:
            continue
        seen.add(ev.id)

        match ev.type:
            case "agent.message":
                for block in ev.content:
                    if block.type == "text":
                        print(block.text, end="")

            case "agent.tool_use":
                print(f"\n  [built-in: {ev.name}]")

            case "agent.custom_tool_use":
                custom_calls[ev.id] = ev
                print(f"\n  → {ev.name}({json.dumps(ev.input)[:80]}...)")

            case "session.status_idle":
                if ev.stop_reason and ev.stop_reason.type == "end_turn":
                    break
                if ev.stop_reason and ev.stop_reason.type == "requires_action":
                    for event_id in ev.stop_reason.event_ids:
                        call = custom_calls[event_id]
                        result = handle_custom_tool(call.name, call.input)
                        client.beta.sessions.events.send(
                            session.id,
                            events=[{
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": event_id,
                                "content": [{
                                    "type": "text",
                                    "text": json.dumps(result),
                                }],
                            }],
                        )

# ── 6. Results ──────────────────────────────────────────────────

print(f"\n\n{'='*60}")
print(f"Analysis blocks: {len(analysis_blocks)}")
print(f"Citations: {len(citations)}")
for block in analysis_blocks:
    print(f"  [{block['block_type']}] {block.get('title', block.get('name', ''))}")
for cit in citations[:5]:
    print(f"  [cite:{cit['id']}] p.{cit['page_number']}: {cit['citedText'][:60]}...")
```

---

## 5. Data Analyst Pipeline

Adapted from the [Data Analyst Agent cookbook](https://platform.claude.com/cookbook/managed-agents-data-analyst-agent).
This is the full pipeline that replaces your current `POST /api/analysis/run`.

```python
# The agent and environment from sections 2-4 above.
# Key difference from the generic data analyst template:
# - PDF-native (pymupdf for extraction, react-pdf-highlighter for display)
# - Citations are first-class (extract_citations tool)
# - analysis_blocks match your frontend Canvas component schema
# - Narrative references citations by [cite:N]

# Reusable session factory
def create_analysis_session(
    pdf_file_id: str,
    pdf_filename: str,
    title: str = "Financial Analysis",
) -> str:
    session = client.beta.sessions.create(
        environment_id=env.id,
        agent={"type": "agent", "id": AGENT_ID, "version": AGENT_VERSION},
        resources=[
            {"type": "file", "file_id": pdf_file_id,
             "mount_path": f"documents/{pdf_filename}"},
        ],
        title=title,
    )
    return session.id


def run_analysis(session_id: str, prompt: str) -> dict:
    """Drive a full analysis and return {blocks, citations, narrative}."""
    blocks, cites, narrative_parts = [], [], []
    # ... (same streaming loop as quickstart above)
    return {
        "analysis_blocks": blocks,
        "citations": cites,
        "narrative": "".join(narrative_parts),
    }
```

### Mapping to your frontend

The `analysis_blocks` returned match your existing `Canvas` component expectations:

| Tool call | Frontend component |
|---|---|
| `generate_chart` → `{block_type: "chart", chart_type, data}` | `ChartRenderer` dispatches to Recharts |
| `generate_table` → `{block_type: "table", columns, data}` | `TableRenderer` |
| `generate_metric` → `{block_type: "metric", name, value}` | `MetricCard` / `MetricGrid` |
| `extract_citations` → `{id, citedText, page_number}` | `CitationContext.addCitations` → `PDFViewer` highlights |
| Agent text with `[cite:N]` markers | `TextWithCitations` / `MarkdownRenderer` |

---

## 6. Prompt Versioning & Rollback

Adapted from the [Prompt Versioning cookbook](https://platform.claude.com/cookbook/managed-agents-cma-prompt-versioning-and-rollback).
Use this to iterate on analysis quality without redeploying.

```python
# ── Ship v2: add sentiment analysis to the prompt ───────────────

V2_SYSTEM = FDAS_SYSTEM_PROMPT + """

## Additional: Sentiment Analysis
When analyzing earnings transcripts or MD&A sections, also assess:
- Management tone (confident, cautious, defensive)
- Forward-looking language strength
- Hedging frequency ("may", "could", "approximately")
Report sentiment as a metric block with name="Management Sentiment"
and value as one of: "Bullish", "Neutral", "Cautious", "Bearish".
"""

updated_agent = client.beta.agents.update(
    AGENT_ID,
    version=AGENT_VERSION,
    system=V2_SYSTEM,
)
print(f"Agent updated to v{updated_agent.version}")

# ── Score v1 vs v2 against a test set ───────────────────────────

TEST_DOCS = [
    {"file_id": "file_abc", "name": "apple-10k.pdf",
     "expected_charts": 4, "expected_citations": 8},
    {"file_id": "file_def", "name": "jpmorgan-earnings.pdf",
     "expected_charts": 3, "expected_citations": 6},
]


def score_version(version: int) -> dict:
    results = {}
    for doc in TEST_DOCS:
        session = client.beta.sessions.create(
            environment_id=env.id,
            agent={"type": "agent", "id": AGENT_ID, "version": version},
            resources=[
                {"type": "file", "file_id": doc["file_id"],
                 "mount_path": f"documents/{doc['name']}"},
            ],
        )
        # Run analysis, count blocks and citations...
        result = run_analysis(session.id, f"Analyze /mnt/session/uploads/documents/{doc['name']}")
        results[doc["name"]] = {
            "charts": len([b for b in result["analysis_blocks"]
                          if b["block_type"] == "chart"]),
            "citations": len(result["citations"]),
            "has_narrative": len(result["narrative"]) > 100,
        }
        client.beta.sessions.archive(session.id)
    return results


v1_scores = score_version(version=1)
v2_scores = score_version(version=updated_agent.version)

# Compare and decide whether to promote v2
for doc_name in v1_scores:
    v1 = v1_scores[doc_name]
    v2 = v2_scores[doc_name]
    print(f"{doc_name}:")
    print(f"  v1: {v1['charts']} charts, {v1['citations']} citations")
    print(f"  v2: {v2['charts']} charts, {v2['citations']} citations")

# ── Roll back if needed ─────────────────────────────────────────

# Production sessions always pin to a specific version:
safe_session = client.beta.sessions.create(
    environment_id=env.id,
    agent={"type": "agent", "id": AGENT_ID, "version": 1},  # pinned
    resources=[...],
)
```

---

## 7. Iterate — Fix Failing Citations

Adapted from the [Iterate cookbook](https://platform.claude.com/cookbook/managed-agents-cma-iterate-fix-failing-tests).
The agent reads a PDF, extracts citations, validates them, and iterates
until all citations resolve correctly.

```python
CITATION_VALIDATOR_SYSTEM = """\
You are a citation validation agent for the FDAS platform.
Given a PDF document and a set of citations, verify that each citation:
1. The cited_text actually appears on the stated page_number
2. The page_number is within the document's page range
3. The display_text is a reasonable summary of the cited_text

Run validation with Python (pymupdf). Read each page, search for the
cited text. If a citation fails, fix it:
- Wrong page? Find the correct page.
- Text not found? Find the closest match.
- Display text misleading? Rewrite it.

Write corrected citations to /mnt/session/outputs/validated_citations.json.
Stop when every citation passes.
"""

validator_agent = client.beta.agents.create(
    name="fdas-citation-validator",
    model=MODEL,
    system=CITATION_VALIDATOR_SYSTEM,
    tools=[
        {
            "type": "agent_toolset_20260401",
            "default_config": {
                "enabled": True,
                "permission_policy": {"type": "always_allow"},
            },
        },
    ],
)

# Mount the PDF + the citations from a previous analysis
session = client.beta.sessions.create(
    environment_id=env.id,
    agent={"type": "agent", "id": validator_agent.id,
           "version": validator_agent.version},
    resources=[
        {"type": "file", "file_id": pdf_file.id,
         "mount_path": "documents/report.pdf"},
        {"type": "file", "file_id": citations_file_id,
         "mount_path": "citations/raw_citations.json"},
    ],
    title="Validate citations",
)

# The iterate loop: agent reads, validates, fixes, re-validates
with client.beta.sessions.events.stream(session.id) as stream:
    client.beta.sessions.events.send(
        session.id,
        events=[{
            "type": "user.message",
            "content": [{
                "type": "text",
                "text": (
                    "Validate every citation in "
                    "/mnt/session/uploads/citations/raw_citations.json "
                    "against /mnt/session/uploads/documents/report.pdf. "
                    "Fix any that fail and save the validated set to "
                    "/mnt/session/outputs/validated_citations.json."
                ),
            }],
        }],
    )
    for ev in stream:
        match ev.type:
            case "agent.message":
                for b in ev.content:
                    if b.type == "text":
                        print(b.text, end="")
            case "agent.tool_use":
                print(f"\n  [{ev.name}]")
            case "session.status_idle":
                if ev.stop_reason and ev.stop_reason.type == "end_turn":
                    break
```

---

## 8. Human-in-the-Loop — Narrative Review Gate

Adapted from the [SRE Incident Responder](https://platform.claude.com/cookbook/managed-agents-sre-incident-responder)
and [Gate cookbook](https://platform.claude.com/cookbook/managed-agents-cma-gate-human-in-the-loop).

The agent completes analysis, then pauses for human review before
the narrative is published.

```python
# The request_review custom tool is already defined in the agent.
# When the agent calls it, the session goes idle with
# stop_reason.type == "requires_action".

# Your application (Next.js API route or FastAPI endpoint):

def handle_review_request(session_id: str, event_id: str, summary: str):
    """Called when the agent requests a review."""
    # Show in your UI: the summary, the generated charts, the citations
    # The reviewer can approve, reject, or request changes.
    pass


def submit_review(session_id: str, event_id: str, decision: str,
                  feedback: str = ""):
    """Called from your review UI."""
    client.beta.sessions.events.send(
        session_id,
        events=[{
            "type": "user.custom_tool_result",
            "custom_tool_use_id": event_id,
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "decision": decision,  # "approved" | "revise" | "rejected"
                    "feedback": feedback,
                }),
            }],
        }],
    )
    # If "revise", the agent continues with the feedback.
    # If "approved", the agent saves final outputs.
    # If "rejected", the agent stops.
```

---

## 9. Production Setup — Webhooks & Vaults

Adapted from [Production Setup](https://platform.claude.com/cookbook/managed-agents-cma-operate-in-production).

### Vault for per-user API credentials

```python
vault = client.beta.vaults.create(
    display_name="FDAS User: analyst@acme.com",
    metadata={"user_id": "user_123", "org": "acme"},
)

# If using Supabase MCP for document storage:
credential = client.beta.vaults.credentials.create(
    vault_id=vault.id,
    display_name="Supabase",
    auth={
        "type": "static_bearer",
        "mcp_server_url": "https://your-project.supabase.co/mcp/",
        "token": SUPABASE_SERVICE_KEY,
    },
)
```

### Webhook handler (FastAPI)

```python
from fastapi import FastAPI, Header, HTTPException, Request
import hmac, hashlib

app = FastAPI()
WEBHOOK_SECRET = "whsec_..."  # from Anthropic Console


@app.post("/webhooks/anthropic")
async def receive_webhook(
    req: Request,
    x_anthropic_signature: str = Header(),
):
    body = await req.body()
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, x_anthropic_signature):
        raise HTTPException(401)

    event = json.loads(body)
    session_id = event["resource_id"]

    if event["event_type"] == "session.status_idled":
        events = client.beta.sessions.events.list(session_id)
        pending_reviews = [
            e for e in events.data
            if e.type == "agent.custom_tool_use"
            and e.name == "request_review"
        ]
        if pending_reviews:
            for review in pending_reviews:
                # Push to your review queue / Slack / email
                await notify_reviewer(
                    session_id=session_id,
                    event_id=review.id,
                    summary=review.input.get("summary", ""),
                )
        else:
            # Analysis complete, no review needed
            await finalize_analysis(session_id)

    return {"ok": True}
```

### Triggering analysis from your Next.js frontend

```typescript
// In your workspace/page.tsx or an API route:

async function startManagedAnalysis(documentId: string, pdfFileId: string) {
  const response = await fetch("/api/managed-analysis", {
    method: "POST",
    body: JSON.stringify({ documentId, pdfFileId }),
  });
  const { sessionId } = await response.json();

  // Open SSE stream for real-time updates
  const eventSource = new EventSource(
    `/api/managed-analysis/${sessionId}/stream`
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case "agent.message":
        // Append to chat messages
        break;
      case "agent.custom_tool_use":
        if (data.name === "generate_chart") {
          // Add to analysis_blocks for Canvas
        } else if (data.name === "extract_citations") {
          // Add to CitationContext
        }
        break;
      case "session.status_idle":
        eventSource.close();
        break;
    }
  };
}
```

---

## 10. Custom Tools Reference

Summary of all custom tools and how they map to your FDAS frontend.

| Tool | Purpose | Frontend Consumer | Returns |
|---|---|---|---|
| `generate_chart` | Create a Recharts-compatible chart block | `Canvas` → `ChartRenderer` | `{block_id, status}` |
| `generate_table` | Create a data table block | `Canvas` → `TableRenderer` | `{block_id, status}` |
| `generate_metric` | Create a metric card | `Canvas` → `MetricCard` | `{block_id, status}` |
| `extract_citations` | Locate text in PDF for highlighting | `CitationContext` → `PDFViewer` | `{citation_id, citation_number}` |
| `request_review` | Pause for human approval | Review UI / Slack | `{decision, feedback}` |

### analysis_blocks schema (matches your existing frontend)

```typescript
interface AnalysisBlock {
  id: string;
  block_type: "chart" | "table" | "metric" | "text_summary";
  // Chart-specific
  chart_type?: "bar" | "multiBar" | "line" | "pie" | "area" | "stackedArea" | "scatter";
  title?: string;
  config?: { xAxisKey: string };
  data?: Record<string, any>[];
  // Table-specific
  columns?: { key: string; label: string }[];
  // Metric-specific
  name?: string;
  value?: string;
  change?: string;
  period?: string;
}
```

### Citation schema (matches your existing CitationContext)

```typescript
interface ManagedAgentCitation {
  id: string;                 // "cite-1", "cite-2", ...
  highlightId: string;        // Same as id
  documentId: string;         // From extract_citations input
  citedText: string;          // Exact PDF text
  displayText: string;        // Human-readable version
  type: "page_location";
  page_number: number;
  rects: CitationRect[];      // Resolved by frontend text search
  searchableText?: string;    // For react-pdf-highlighter matching
}
```

---

## Architecture Decision: Hybrid vs Full Migration

You don't have to replace your entire FastAPI backend. Consider:

### Option A: Hybrid (recommended for incremental adoption)
- Keep your FastAPI backend for document CRUD, auth, and the DB
- Use Managed Agents for the analysis pipeline only
- Your backend creates sessions and relays events to the frontend
- Citations and analysis_blocks flow through your existing WebSocket

### Option B: Full Migration
- Replace the FastAPI Claude/LangGraph layer entirely
- Next.js API routes proxy to the Managed Agents API
- Keep FastAPI only for document storage and user management

### Option C: Managed Agents as a Premium Tier
- Existing analysis via your backend (current flow)
- "Deep Analysis" mode routes through Managed Agents for longer,
  more thorough analysis with iterate-until-correct citations

---

## Resources

- [Managed Agents Quickstart](https://platform.claude.com/docs/en/managed-agents/quickstart)
- [Data Analyst Agent Cookbook](https://platform.claude.com/cookbook/managed-agents-data-analyst-agent)
- [Prompt Versioning Cookbook](https://platform.claude.com/cookbook/managed-agents-cma-prompt-versioning-and-rollback)
- [SRE Incident Responder](https://platform.claude.com/cookbook/managed-agents-sre-incident-responder)
- [Iterate Cookbook](https://platform.claude.com/cookbook/managed-agents-cma-iterate-fix-failing-tests)
- [Production Setup](https://platform.claude.com/cookbook/managed-agents-cma-operate-in-production)
- [Scaling Managed Agents (Engineering Blog)](https://www.anthropic.com/engineering/managed-agents)



FINANCIAL_ANALYSIS_SKILL = """\
---
name: fdas-financial-analysis
description: Conventions for analyzing financial documents in the FDAS platform.
---

# Financial Document Analysis Conventions

Removed fdas-financial-analysis from skills — the agent will save now.
To add it back later, run this once in your backend to create the skill in your workspace:

... (skill content from §3 of your FDAS doc)
"""

skill = client.beta.skills.create(
    display_title="fdas-financial-analysis",
    files=[
        ("fdas-financial-analysis/SKILL.md",
         FINANCIAL_ANALYSIS_SKILL.encode(),
         "text/markdown"),
    ],
    betas=["skills-2025-10-02"],
)
print(f"Skill created: {skill.id}")

Then update the agent to re-add it:

client.beta.agents.update(
    AGENT_ID,
    skills=[
        {"type": "anthropic", "skill_id": "pdf"},
        {"type": "anthropic", "skill_id": "xlsx"},
        {"type": "custom", "skill_id": skill.id, "version": "latest"},
    ],
    betas=["managed-agents-2026-04-01"],
)