graph TD
    subgraph Frontend: Next.js/React
        UI[User Interface - e.g., Chat Input, Button] --> Comp{Page/Component containing Canvas};
        Comp -- User Action e.g., Submit Query --> APIClient[analysis.ts];
        APIClient -- Calls runAnalysis --> BackendAPI[Backend API Endpoint /api/analysis/run];
        BackendAPI -- Returns AnalysisResult --> APIClient;
        APIClient -- Processes Response --> Canvas[Canvas.tsx]; 
        Canvas -- Processes AnalysisResult/Messages --> VizData["Processed VisualizationData [Charts, Tables, Metrics]"]; 
        VizData -- Passes ChartData --> ChartDispatcher[ChartRenderer.tsx];
        VizData -- Passes TableData --> TableRend[TableRenderer.tsx];
        VizData -- Passes Metrics --> MetricGridComp[MetricGrid.tsx];
        ChartDispatcher -- Selects Chart based on chartType --> SpecificChart[Specific Chart e.g., BarChart.tsx];
        SpecificChart -- Renders using recharts --> RenderedChart[Rendered Chart in UI];
        TableRend -- Renders Table --> RenderedTable[Rendered Table in UI];
        MetricGridComp -- Renders Metrics --> RenderedMetrics[Rendered Metrics in UI];

        %% Fallback Data Extraction [Less Ideal Path]
        Canvas -- If no structured VizData --> ExtractFunc[extractFinancialDataFromMessages];
        ExtractFunc -- Extracts basic data from text --> VizData;
    end

    subgraph Backend: Python/Langchain/LangGraph
        BackendAPI -- Receives Request --> Agent[AI Agent - LangGraph];
        Agent -- Retrieves Docs --> DataSource[[Document Source]];
        Agent -- Analysis Request + Tool Schema --> LLM[Anthropic LLM];
        LLM -- Asks to use Tool --> Agent;
        Agent -- Invokes Tool Call --> LLM;
        LLM -- Returns Structured JSON (Chart Table Data ) --> Agent; 
        Agent -- Collects Text Analysis & Structured Data --> BackendAPI;
    end

    style Agent fill:#f9d,stroke:#333,stroke-width:2px
    style LLM fill:#ccf,stroke:#333,stroke-width:2px
    style APIClient fill:#lightgrey,stroke:#333,stroke-width:1px
    style Canvas fill:#lightgrey,stroke:#333,stroke-width:1px
    style ChartDispatcher fill:#lightgrey,stroke:#333,stroke-width:1px
    style SpecificChart fill:#lightgrey,stroke:#333,stroke-width:1px
    style DataSource fill:#eee,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5
    style VizData fill:#e6f0ff,stroke:#333,stroke-width:1px