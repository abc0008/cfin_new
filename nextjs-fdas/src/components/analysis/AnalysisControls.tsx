'use client';

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings } from 'lucide-react';
import { cn } from "@/lib/utils";

interface AnalysisControlsProps {
  onRunAnalysis: (
    analysisType: string, 
    knowledgeBase?: string, 
    userQuery?: string
  ) => void;
  isLoading: boolean;
}

const analysisTypes = [
  { value: 'basic_financial', label: 'Basic Financial Analysis' },
  { value: 'comprehensive_tools', label: 'Comprehensive Analysis' },
  { value: 'financial_template', label: 'Template-Driven Financial Analysis' },
  { value: 'sentiment_analysis', label: 'Sentiment Analysis' },
];

export const AnalysisControls: React.FC<AnalysisControlsProps> = ({ 
  onRunAnalysis,
  isLoading 
}) => {
  const [analysisType, setAnalysisType] = useState<string>('basic_financial');
  const [isAdvancedOpen, setIsAdvancedOpen] = useState<boolean>(false);
  const [knowledgeBase, setKnowledgeBase] = useState<string>('');
  const [userQuery, setUserQuery] = useState<string>('');

  const advancedOptionsFilled = knowledgeBase.trim() !== '' || userQuery.trim() !== '';

  useEffect(() => {
    if (!analysisTypes.some((type) => type.value === analysisType)) {
      setAnalysisType(analysisTypes[0].value);
    }
  }, [analysisType]);

  const handleRunAnalysis = () => {
    if (isLoading) return;

    onRunAnalysis(
      analysisType,
      knowledgeBase.trim() || undefined,
      userQuery.trim() || undefined
    );
  };
  
  return (
    <div className="workspace-summary-block w-full border p-4">
      <div className="flex flex-col space-y-4">
        <div className="flex items-center gap-4">
          <div className="min-w-0 flex-shrink border-b border-border pb-2">
            <h2 className="text-xl font-avenir-pro-demi text-foreground">Analysis Controls</h2>
          </div>

          <div className="flex-1 min-w-[200px] flex items-center gap-2">
            <label className="text-xs font-avenir-pro-demi text-foreground flex-shrink-0">
              Analysis Type:
            </label>
            <Select value={analysisType} onValueChange={setAnalysisType} disabled={isLoading}>
              <SelectTrigger className="fdas-select min-w-0 flex-1 border border-border bg-background px-3 py-1 text-sm font-avenir-pro text-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring">
                <SelectValue placeholder="Select analysis type" />
              </SelectTrigger>
              <SelectContent className="workspace-panel font-avenir-pro bg-background">
                {analysisTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value} className="text-sm">
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Popover open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
            <PopoverTrigger asChild>
              <Button 
                variant="outline" 
                size="sm" 
                className={cn(
                  "workspace-secondary-btn ml-2 flex h-8 flex-shrink-0 items-center px-3 py-1 text-xs font-avenir-pro",
                  advancedOptionsFilled &&
                    "border-accent bg-accent text-accent-foreground hover:bg-accent/90"
                )}
              >
                <Settings className="h-3.5 w-3.5 mr-1.5" />
                <span>Advanced Options</span>
              </Button>
            </PopoverTrigger>
            <PopoverContent
              className="workspace-panel mt-2 w-[500px] rounded-xl border border-border bg-card p-4 shadow-none"
              align="center"
              sideOffset={10}
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-avenir-pro-demi text-foreground mb-1">
                    Knowledge Base (Optional)
                  </label>
                  <Textarea
                    placeholder="Enter custom knowledge base information..."
                    value={knowledgeBase}
                    onChange={(e) => setKnowledgeBase(e.target.value)}
                    disabled={isLoading}
                    className="fdas-textarea min-h-[100px] font-avenir-pro"
                  />
                  <p className="text-xs text-muted-foreground mt-1 font-avenir-pro">
                    Provide domain-specific knowledge to enhance the analysis.
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-avenir-pro-demi text-foreground mb-1">
                    Custom Query (Optional)
                  </label>
                  <Textarea
                    placeholder="Enter a specific query for the document..."
                    value={userQuery}
                    onChange={(e) => setUserQuery(e.target.value)}
                    disabled={isLoading}
                    className="fdas-textarea min-h-[100px] font-avenir-pro"
                  />
                  <p className="text-xs text-muted-foreground mt-1 font-avenir-pro">
                    Specify a custom question to analyze in the document.
                  </p>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          <div className="flex-shrink-0">
            <Button
              type="button"
              onClick={handleRunAnalysis}
              disabled={isLoading}
              className="workspace-primary-btn"
            >
              {isLoading ? 'Running Analysis...' : 'Run Analysis'}
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}; 
