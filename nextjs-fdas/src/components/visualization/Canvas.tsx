'use client';

import React, { useState, useCallback } from 'react';
import { AnalysisResult } from '@/types';
import { ChartData, TableData, VisualizationData, FinancialMetric } from '@/types/visualization';
import ChartRenderer from '../charts/ChartRenderer';
import TableRenderer from '../tables/TableRenderer';
import MetricCard from '../metrics/MetricCard';
import MetricGrid from '../metrics/MetricGrid';

interface CanvasProps {
  analysisResults: AnalysisResult[];
  messages?: any[]; // Add messages prop
  loading?: boolean;
  error?: Error | string;
  onCitationClick?: (highlightId: string) => void;
}

/**
 * Canvas component for managing the layout and navigation of multiple visualizations
 */
const Canvas: React.FC<CanvasProps> = ({ analysisResults, messages = [], loading, error, onCitationClick }) => {
  const [currentTab, setCurrentTab] = useState<'overview' | 'charts' | 'tables'>('overview');

  const handleDataPointClick = (dataPoint: any) => {
    if (dataPoint && dataPoint.citation && onCitationClick) {
      onCitationClick(dataPoint.citation.highlightId);
    }
  };

  // NOTE: The following extensive regex-based extraction functions (extractFinancialDataFromMessages and its helpers)
  // have been removed as Canvas.tsx now relies solely on structured data (analysis_blocks or visualizationData)
  // from upstream sources (messages or analysisResults). This simplifies Canvas.tsx and removes brittle regex parsing.
  // Original functions removed:
  // - extractFinancialDataFromMessages
  // - extractIncomeStatementData
  // - createVisualizationFromDetailedItems
  // - createVisualizationFromDirectMatches
  // - extractFinancialMetric
  // - extractNamedFinancialMetric
  // - And potentially normalizeToMillions, calculatePercentChange if they were exclusively used by the above.
  //   (Further check needed if these two helpers are used elsewhere before full removal)

  // Process analysis results into visualization data
  const processAnalysisResults = useCallback((results: AnalysisResult[], msgs: any[]) => {
    // Check for analysis_blocks in messages first
    if (msgs.length > 0) {
      console.log(`Checking ${msgs.length} messages for visualization data...`);
      
      // Find the latest assistant message with analysis_blocks
      for (let i = msgs.length - 1; i >= 0; i--) {
        const msg = msgs[i];
        if (msg.role === 'assistant') {
          console.log(`Examining assistant message ${i}:`, 
                      msg.id ? `ID: ${msg.id}` : 'No ID',
                      msg.analysis_blocks ? `Has ${msg.analysis_blocks.length} analysis blocks` : 'No analysis blocks');
          
          if (msg.analysis_blocks && msg.analysis_blocks.length > 0) {
            console.log(`Found ${msg.analysis_blocks.length} analysis blocks in message ${msg.id || i}`);
            
            const charts: ChartData[] = [];
            const tables: TableData[] = [];
            const metrics: FinancialMetric[] = [];
            
            // Detailed logging of block structure
            console.log('Analysis blocks structure:', JSON.stringify(msg.analysis_blocks[0], null, 2).substring(0, 200) + '...');
            
            // Convert analysis blocks to the expected visualization data format
            msg.analysis_blocks.forEach((block, index) => {
              console.log(`Processing analysis block ${index}: type=${block.block_type}, title=${block.title || 'No title'}`);
              
              // Extract charts
              if (block.block_type === 'chart' && block.content) {
                // Check the structure to determine where the chart data is stored
                if (block.content.chart_data) {
                  console.log(`Found chart data in block ${index}: ${block.content.chart_data.chartType}`);
                  charts.push(block.content.chart_data);
                } else if (block.content.chartType) {
                  // Direct chart data structure
                  console.log(`Found direct chart data in block ${index}: ${block.content.chartType}`);
                  charts.push(block.content);
                }
              }
              
              // Extract tables
              if (block.block_type === 'table' && block.content) {
                // Check the structure to determine where the table data is stored
                if (block.content.table_data) {
                  console.log(`Found table data in block ${index}: ${block.content.table_data.tableType}`);
                  tables.push(block.content.table_data);
                } else if (block.content.tableType) {
                  // Direct table data structure
                  console.log(`Found direct table data in block ${index}: ${block.content.tableType}`);
                  tables.push(block.content);
                }
              }
              
              // Extract metrics if available
              if (block.content && block.content.metrics) {
                console.log(`Found ${block.content.metrics.length} metrics in block ${index}`);
                metrics.push(...block.content.metrics);
              }
            });
            
            // Return visualization data extracted from analysis blocks
            console.log(`Returning visualization data from analysis_blocks: ${charts.length} charts, ${tables.length} tables, ${metrics.length} metrics`);
            return {
              charts,
              tables,
              metrics,
              analysisText: msg.analysis_blocks.find(b => b.block_type === 'text_summary')?.content || undefined
            };
          }
        }
      }
    }

    // If we have analysis results with visualization data, use them
    if (results.length) {
      const latestResult = results[results.length - 1];
      
      // Add safety check for latestResult
      if (latestResult) {
        // Tool-based visualization format
        if (latestResult.visualizationData && (
          (Array.isArray(latestResult.visualizationData.charts) && latestResult.visualizationData.charts.length > 0) ||
          (Array.isArray(latestResult.visualizationData.tables) && latestResult.visualizationData.tables.length > 0) ||
          (Array.isArray(latestResult.metrics) && latestResult.metrics.length > 0)
        )) {
          console.log('Using tool-based visualization format from analysis result');
          return {
            charts: latestResult.visualizationData.charts || [],
            tables: latestResult.visualizationData.tables || [],
            metrics: latestResult.metrics || [],
            monetaryValues: latestResult.visualizationData.monetaryValues,
            percentages: latestResult.visualizationData.percentages,
            keywordFrequency: latestResult.visualizationData.keywordFrequency,
            analysisText: latestResult.analysisText
          };
        }
        // Legacy format: metrics, charts, tables as top-level properties
        if ((latestResult.metrics?.length || latestResult.visualizationData?.charts?.length || latestResult.visualizationData?.tables?.length)) {
          console.log('Using legacy visualization format from analysis result');
          return {
            charts: latestResult.visualizationData?.charts || [],
            tables: latestResult.visualizationData?.tables || [],
            metrics: latestResult.metrics || [],
            analysisText: latestResult.analysisText
          };
        }
      }
    }
    
    // If we couldn't find any structured data from analysis results or messages, return empty visualization data
    console.log('No structured visualization data found in messages or analysis results, returning empty structure');
    return {
      charts: [],
      tables: [],
      metrics: [],
      analysisText: undefined
    };
  }, []);

  const visualizationData = processAnalysisResults(analysisResults, messages);

  if (loading) {
    return (
      <div role="status" aria-label="Loading visualizations" className="flex items-center justify-center p-8 bg-muted/20 rounded-lg min-h-[600px]">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-8 w-40 bg-muted rounded mb-4" />
          <div className="h-80 w-full bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="flex items-center justify-center p-8 bg-destructive/10 rounded-lg min-h-[600px]">
        <div className="text-destructive text-center">
          <h3 className="font-avenir-pro-demi mb-2">Error loading visualizations</h3>
          <p className="text-sm font-avenir-pro">{error.toString()}</p>
        </div>
      </div>
    );
  }

  if (!visualizationData || 
      ((!visualizationData.charts || visualizationData.charts.length === 0) && 
       (!visualizationData.tables || visualizationData.tables.length === 0) && 
       (!visualizationData.metrics || visualizationData.metrics.length === 0))) {
    return (
      <div role="status" aria-label="No data" className="flex items-center justify-center p-8 bg-muted/20 rounded-lg min-h-[600px]">
        <p className="text-muted-foreground font-avenir-pro">No visualization data available. Try asking a question that requires charts or tables.</p>
      </div>
    );
  }

  return (
    <div role="main" className="w-full rounded-lg bg-card shadow-sm">
      <div className="border-b border-border">
        <div role="tablist" className="flex space-x-4 px-4">
          <button
            role="tab"
            aria-selected={currentTab === 'overview'}
            aria-controls="overview-panel"
            className={`py-4 px-1 text-sm font-avenir-pro-demi transition-colors ${
              currentTab === 'overview'
                ? 'text-primary border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground hover:border-border'
            }`}
            onClick={() => setCurrentTab('overview')}
          >
            Overview
          </button>
          <button
            role="tab"
            aria-selected={currentTab === 'charts'}
            aria-controls="charts-panel"
            className={`py-4 px-1 text-sm font-avenir-pro-demi transition-colors ${
              currentTab === 'charts'
                ? 'text-primary border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground hover:border-border'
            }`}
            onClick={() => setCurrentTab('charts')}
          >
            Charts ({visualizationData.charts?.length || 0})
          </button>
          <button
            role="tab"
            aria-selected={currentTab === 'tables'}
            aria-controls="tables-panel"
            className={`py-4 px-1 text-sm font-avenir-pro-demi transition-colors ${
              currentTab === 'tables'
                ? 'text-primary border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground hover:border-border'
            }`}
            onClick={() => setCurrentTab('tables')}
          >
            Tables ({visualizationData.tables?.length || 0})
          </button>
        </div>
      </div>

      <div className="p-4 overflow-y-auto max-h-[calc(100vh-200px)]">
        {currentTab === 'overview' ? (
          <div className="space-y-6">
            <MetricGrid 
              metrics={visualizationData.metrics || []}
              title="Key Performance Indicators"
            />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {visualizationData.charts && visualizationData.charts.length > 0 && (
                <ChartRenderer data={visualizationData.charts[0]} onDataPointClick={handleDataPointClick} />
              )}
              {visualizationData.charts && visualizationData.charts.length > 1 && (
                <ChartRenderer data={visualizationData.charts[1]} onDataPointClick={handleDataPointClick} />
              )}
            </div>
            
            {visualizationData.tables && visualizationData.tables.length > 0 && (
              <TableRenderer data={visualizationData.tables[0]} />
            )}
            
            {/* Display Analysis Text if available */}
            {visualizationData.analysisText && (
              <div className="mt-6 p-4 bg-muted/30 rounded-lg shadow-sm border border-border">
                <h4 className="text-md font-avenir-pro-demi text-foreground mb-2">Textual Summary</h4>
                <p className="text-sm font-avenir-pro text-muted-foreground whitespace-pre-wrap">
                  {visualizationData.analysisText}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div
            role="tabpanel"
            id={`${currentTab}-panel`}
            aria-labelledby={`${currentTab}-tab`}
            className="grid grid-cols-1 lg:grid-cols-2 gap-4"
          >
            {currentTab === 'charts' ? 
              (visualizationData.charts || []).map((chart, index) => (
                <div key={index} className="col-span-1">
                  <ChartRenderer data={chart} onDataPointClick={handleDataPointClick} />
                </div>
              )) :
              (visualizationData.tables || []).map((table, index) => (
                <div key={index} className="col-span-1">
                  <TableRenderer data={table} />
                </div>
              ))
            }
          </div>
        )}
      </div>
    </div>
  );
};

export default Canvas; 
