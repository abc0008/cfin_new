# Financial Document Analysis System (FDAS)

## Overview

The Financial Document Analysis System (FDAS) is an AI-powered application designed to revolutionize financial document analysis. It combines robust PDF processing with a conversational AI interface and dynamic data visualization. Users can upload financial documents, perform structured analysis, and interact with data through a visually engaging and highly interactive interface.

FDAS leverages state-of-the-art AI services, including the Claude API for advanced PDF support and citation extraction, and pre-built conversational agents from LangGraph, with orchestration provided by LangChain. The system is built with a FastAPI backend and a Next.js frontend.

## Key Features

*   **Document Processing**:
    *   Secure PDF upload and processing.
    *   Extraction of text, tables, and embedded citations using Claude API.
    *   Support for multiple documents per session.
    *   Storage of processed documents for future reference.
    *   Contextual links and highlights connecting document content to analysis results.
*   **Conversational Interface**:
    *   Stateful chatbot with multi-turn conversation and context retention.
    *   Citation linking: users can reference highlighted PDF sections in the conversation.
    *   Guided financial analysis prompts.
    *   Full conversation history with citation references.
*   **Financial Analysis Capabilities**:
    *   Ratio and trend analysis on financial statements.
    *   Identification of key performance indicators (KPIs) and industry benchmarks.
    *   Comparison of results to detect anomalies and significant data shifts.
    *   Integration with LangGraph pre-built agents for common financial analysis tasks.
*   **Interactive Canvas and Visualization**:
    *   Dynamic display of financial analysis results using Recharts.
    *   Support for zooming, filtering, and data exploration.
    *   Exportable visualizations.
    *   Linked PDF annotations and highlighting (inspired by `react-pdf-highlighter`).
*   **Data Validation and Structure**:
    *   Pydantic models for validating input and output data (backend).
    *   Zod schemas for frontend data validation.
    *   Structured output for visualizations and citations.

## Tech Stack

*   **Frontend**:
    *   Next.js
    *   React
    *   TypeScript
    *   Tailwind CSS
    *   Shadcn UI (for UI components like Tabs, Buttons, etc.)
    *   Recharts (for charts)
    *   `react-pdf-highlighter` (for PDF viewing and highlighting)
*   **Backend**:
    *   FastAPI
    *   Python
    *   Pydantic (for data validation)
    *   SQLAlchemy (for ORM)
*   **AI & Orchestration**:
    *   LangChain
    *   LangGraph
    *   Anthropic Claude API
*   **Database**:
    *   PostgreSQL (implied, can be configured via `DATABASE_URL`, supports SQLite for dev/testing)
*   **File Storage**:
    *   Local storage or AWS S3 (configurable via `STORAGE_TYPE`)

## Application Flow

The application facilitates a seamless flow from document upload to interactive analysis and visualization. The diagram below illustrates the high-level interaction between the major components of FDAS:

```mermaid
graph TD
    subgraph "User Interface (Frontend - Next.js)"
        direction LR
        U_Pages["Pages & UI Components\n(Dashboard, Workspace, PDFViewer, ChatInterface, UploadForm)\n`app/.../page.tsx`, `components/...`"]
        U_Canvas["Visualization Canvas\n`components/visualization/Canvas.tsx`"]
        FE_APIClients["Frontend API Clients\n`lib/api/...`"]
    end

    subgraph "Backend (FastAPI)"
        direction LR
        B_APIRoutes["API Routes\n`app/main.py`, `api/router.py`"]
        B_Services["Core Services\n(DocumentService, ConversationService, AnalysisService)\n`services/...`, `pdf_processing/document_service.py`"]
        B_AIEngine["AI Engine\n(LangGraphService, ClaudeService, Tools, Templates)\n`pdf_processing/...`, `models/tools.py`, `data/templates/...`"]
        B_Repositories["Data Repositories\n(DocumentRepository, ConversationRepository, AnalysisRepository)\n`repositories/...`"]
        B_Database["Database\n(SQLAlchemy, models/database_models.py)\n`utils/database.py`"]
        B_Storage["File Storage\n`utils/storage.py`"]
    end

    subgraph "External Services"
        Ext_ClaudeAPI["Claude API"]
    end

    %% User actions trigger frontend components
    UserAction["User Actions (Upload, Chat, Request Analysis)"] --> U_Pages

    %% Frontend UI to Frontend API Clients
    U_Pages --> FE_APIClients
    U_Canvas --> FE_APIClients  // Receives AnalysisResults

    %% Data flow to Canvas for visualization
    U_Pages -- Chat Messages with Analysis Blocks --> U_Canvas
    FE_APIClients -- Analysis Results --> U_Canvas

    %% Frontend API Clients to Backend API Routes
    FE_APIClients --> B_APIRoutes

    %% Backend API Routes to Backend Services
    B_APIRoutes --> B_Services

    %% Backend Services interactions
    B_Services --> B_AIEngine
    B_Services --> B_Repositories
    B_Services --> B_Storage

    %% AI Engine to External Claude API
    B_AIEngine --> Ext_ClaudeAPI

    %% Repositories to Database
    B_Repositories --> B_Database

    %% Styling
    classDef user fill:#FFF5E1,stroke:#FFC300,stroke-width:2px;
    classDef frontend fill:#D6EAF8,stroke:#2E86C1,stroke-width:2px;
    classDef backend fill:#D5F5E3,stroke:#28B463,stroke-width:2px;
    classDef external fill:#EBDEF0,stroke:#8E44AD,stroke-width:2px;

    class UserAction user;
    class U_Pages,U_Canvas,FE_APIClients frontend;
    class B_APIRoutes,B_Services,B_AIEngine,B_Repositories,B_Database,B_Storage backend;
    class Ext_ClaudeAPI external;
```

**Flow Description:**

1.  **User Interaction**: The user interacts with the frontend (e.g., uploads a document, sends a chat message, requests analysis).
2.  **Frontend Processing**:
    *   UI components (`UploadForm`, `ChatInterface`, `AnalysisControls`) handle user input.
    *   Frontend API clients (`lib/api/...`) make requests to the backend.
    *   The `Canvas` component prepares to display data, receiving `AnalysisResults` from API calls or parsing `analysis_blocks` from chat messages.
3.  **Backend API Handling**:
    *   FastAPI routes (`app/main.py`, `api/router.py`) receive requests.
    *   Requests are passed to appropriate backend services (`DocumentService`, `ConversationService`, `AnalysisService`).
4.  **Core Service Logic**:
    *   Services orchestrate business logic, interacting with the AI Engine, Repositories, and Storage.
    *   `DocumentService` handles PDF processing (potentially via `ClaudeService`) and storage.
    *   `ConversationService` manages chat interactions, leveraging `LangGraphService` and `ClaudeService`.
    *   `AnalysisService` performs financial analysis, using `ClaudeService` with specialized tools and templates.
5.  **AI Engine**:
    *   `LangGraphService` manages the state and flow of AI agents.
    *   `ClaudeService` interacts with the Anthropic Claude API for tasks like text extraction, citation generation, financial data extraction (using tools), and chat responses.
6.  **Data Persistence & Retrieval**:
    *   Repositories (`DocumentRepository`, etc.) handle database operations (CRUD) via SQLAlchemy.
    *   The Database stores documents, conversation history, analysis results, and user data.
    *   `StorageService` manages the persistence of PDF files (local or S3).
7.  **Response & Visualization**:
    *   The backend sends processed data (including analysis results, chat responses, visualization data) back to the frontend.
    *   The `Canvas` component on the frontend renders charts, tables, and metrics based on the received data.
    *   `PDFViewer` displays documents with highlighting and citation links.

## System Architecture

FDAS is architected with a decoupled frontend and backend:

*   **Client-Side (Frontend)**: A Next.js application providing the user interface, interactive chat, and visualization canvas. It communicates with the backend via REST APIs.
*   **Server-Side (Backend)**: A FastAPI application serving API endpoints, managing AI interactions, processing documents, performing financial analysis, and handling data persistence.
*   **AI Engine**: Integrated within the backend, this engine uses LangChain and LangGraph for orchestrating AI agents and Claude API for LLM capabilities, PDF processing, and tool usage.
*   **Database**: Stores metadata, processed document content, conversation histories, and analysis results.
*   **External Services**: Primarily the Anthropic Claude API for advanced AI functionalities.

(For a more detailed component-based architecture diagram, please refer to the `ProjectRequirementsDocument.md`.)

## Setup and Installation

### Prerequisites

*   Node.js (v18 or later)
*   npm or yarn
*   Python (v3.9 or later)
*   pip

### Backend Setup

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Set up environment variables:
    *   Copy `.env.example` to `.env`.
    *   Fill in the required variables, especially `ANTHROPIC_API_KEY` and `DATABASE_URL`.
    ```bash
    cp .env.example .env
    # Edit .env with your actual values
    ```
5.  Initialize the database (creates tables):
    ```bash
    python -m utils.init_db
    ```
6.  Run the backend server:
    ```bash
    python run.py
    ```
    The backend will typically run on `http://localhost:8000`.

### Frontend Setup

1.  Navigate to the `nextjs-fdas` directory:
    ```bash
    cd nextjs-fdas
    ```
2.  Install Node.js dependencies:
    ```bash
    npm install
    # or
    yarn install
    ```
3.  Set up environment variables for the frontend:
    *   Create a `.env.local` file in the `nextjs-fdas` directory.
    *   Add `NEXT_PUBLIC_API_URL=http://localhost:8000` (or your backend URL).
4.  Run the frontend development server:
    ```bash
    npm run dev
    # or
    yarn dev
    ```
    The frontend will typically run on `http://localhost:3000`.

## Project Structure

```
cfin/
├── backend/
│   ├── app/                  # FastAPI application core (main.py, routes)
│   ├── data/                 # Templates for analysis
│   ├── database/             # Database session and repository base
│   ├── models/               # Pydantic and SQLAlchemy models
│   ├── pdf_processing/       # Services for PDF processing, Claude, LangGraph
│   ├── repositories/         # Data access layer
│   ├── services/             # Business logic services
│   ├── tests/                # Backend tests
│   ├── utils/                # Utility modules (database, storage, error handling)
│   ├── .env.example          # Environment variable template
│   ├── requirements.txt      # Python dependencies
│   └── run.py                # Script to run the backend server
├── nextjs-fdas/
│   ├── public/               # Static assets
│   ├── src/
│   │   ├── app/              # Next.js App Router (pages, layouts)
│   │   ├── components/       # React components (UI, chat, visualization)
│   │   ├── lib/              # Libraries, API clients, utilities
│   │   ├── services/         # Frontend services (e.g., visualizationService)
│   │   ├── types/            # TypeScript type definitions
│   │   └── validation/       # Zod schemas for frontend validation
│   ├── .env.local.example  # Environment variable template for frontend
│   ├── package.json          # Node.js dependencies and scripts
│   ├── next.config.js        # Next.js configuration
│   └── tailwind.config.js    # Tailwind CSS configuration
└── ProjectRequirementsDocument.md # Project requirements
└── README.md                 # This file
```

## Testing

The project includes a suite of tests for both backend and frontend components:

*   **Backend**:
    *   **Unit Tests**: Located in `backend/tests/unit/`, testing individual modules and functions (e.g., services, models, utilities). Run with `pytest backend/tests/unit`.
    *   **Integration Tests**: Located in `backend/tests/integration/`, verifying interactions between components (e.g., API endpoints with services and database). Run with `pytest backend/tests/integration`.
    *   **Performance Tests**: Located in `backend/tests/performance/`, for assessing the performance of critical endpoints.
    *   Specific test scripts like `claude_test.sh`, `test_document_api_only.sh`, `test_document_persistence.sh`, `test_document_upload.py`, `test_citations_with_pdf.py`, `run_visibility_tests.py` are available for targeted testing.
*   **Frontend**:
    *   **Unit/Integration Tests**: Located in `nextjs-fdas/src/components/.../__tests__` and `nextjs-fdas/src/tests/api`, using Jest and React Testing Library. Run with `npm test` or `yarn test` in the `nextjs-fdas` directory.

(For a detailed testing strategy, refer to the `ProjectRequirementsDocument.md`.)

## Contributing

Contributions are welcome! Please follow the standard GitHub flow:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Commit your changes.
4.  Push to your branch.
5.  Create a Pull Request.

Please ensure your code adheres to the existing style and that all tests pass.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (assuming one would be added).