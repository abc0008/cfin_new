'use client';

import React from 'react';
import { Loader2, BarChart2, Table, TrendingUp } from 'lucide-react';

interface StreamingTextIndicatorProps {
  text: string;
}

export function StreamingTextIndicator({ text }: StreamingTextIndicatorProps) {
  return (
    <div className="relative">
      <div className="whitespace-pre-wrap">{text}</div>
      <div className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
    </div>
  );
}

interface ToolProgressIndicatorProps {
  toolName: string;
  toolId: string;
}

export function ToolProgressIndicator({ toolName, toolId }: ToolProgressIndicatorProps) {
  const getToolIcon = (name: string) => {
    switch (name) {
      case 'generate_graph_data':
        return <BarChart2 className="h-3 w-3" />;
      case 'generate_table_data':
        return <Table className="h-3 w-3" />;
      case 'generate_financial_metric':
        return <TrendingUp className="h-3 w-3" />;
      default:
        return <Loader2 className="h-3 w-3 animate-spin" />;
    }
  };

  const getToolLabel = (name: string) => {
    switch (name) {
      case 'generate_graph_data':
        return 'Creating chart...';
      case 'generate_table_data':
        return 'Building table...';
      case 'generate_financial_metric':
        return 'Calculating metric...';
      default:
        return 'Processing...';
    }
  };

  return (
    <div className="inline-flex items-center px-2 py-1 bg-primary/10 text-primary rounded text-xs">
      {getToolIcon(toolName)}
      <span className="ml-1">{getToolLabel(toolName)}</span>
    </div>
  );
}

interface StreamingMessageProps {
  text: string;
  toolsInProgress: string[];
  showTypingIndicator?: boolean;
}

export function StreamingMessage({ 
  text, 
  toolsInProgress, 
  showTypingIndicator = true 
}: StreamingMessageProps) {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] rounded-lg px-4 py-3 bg-card border border-border text-foreground shadow-sm font-avenir-pro text-sm">
        <div className="whitespace-pre-wrap">
          {text}
          {showTypingIndicator && text && (
            <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
          )}
        </div>
        
        {/* Show tools in progress */}
        {toolsInProgress.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {toolsInProgress.map(toolId => (
              <ToolProgressIndicator 
                key={toolId} 
                toolName="unknown" 
                toolId={toolId} 
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface VisualizationReadyIndicatorProps {
  type: 'chart' | 'table' | 'metric';
  count: number;
}

export function VisualizationReadyIndicator({ type, count }: VisualizationReadyIndicatorProps) {
  const getIcon = () => {
    switch (type) {
      case 'chart':
        return <BarChart2 className="h-4 w-4" />;
      case 'table':
        return <Table className="h-4 w-4" />;
      case 'metric':
        return <TrendingUp className="h-4 w-4" />;
    }
  };

  const getLabel = () => {
    const plural = count !== 1 ? 's' : '';
    switch (type) {
      case 'chart':
        return `${count} chart${plural} ready`;
      case 'table':
        return `${count} table${plural} ready`;
      case 'metric':
        return `${count} metric${plural} ready`;
    }
  };

  return (
    <div className="inline-flex items-center px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
      {getIcon()}
      <span className="ml-1">{getLabel()}</span>
    </div>
  );
}

interface ConnectionStatusProps {
  isConnected: boolean;
  isStreaming: boolean;
}

export function ConnectionStatus({ isConnected, isStreaming }: ConnectionStatusProps) {
  const getStatus = () => {
    if (isStreaming) return { label: 'Streaming', color: 'text-blue-600 bg-blue-500' };
    if (isConnected) return { label: 'Connected', color: 'text-green-600 bg-green-500' };
    return { label: 'Disconnected', color: 'text-red-600 bg-red-500' };
  };

  const status = getStatus();

  return (
    <div className={`flex items-center text-xs ${status.color.split(' ')[0]}`}>
      <div className={`w-2 h-2 rounded-full mr-1 ${status.color.split(' ')[1]}`} />
      {status.label}
    </div>
  );
}