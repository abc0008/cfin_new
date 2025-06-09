'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings, ChevronDown, ChevronUp } from 'lucide-react';
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
  { value: 'comprehensive', label: 'Comprehensive Analysis' },
  { value: 'ratio_analysis', label: 'Financial Ratios' },
  { value: 'trend_analysis', label: 'Trend Analysis' },
  { value: 'benchmarking', label: 'Industry Benchmarking' },
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

  const handleRunAnalysis = () => {
    onRunAnalysis(
      analysisType,
      knowledgeBase.trim() || undefined,
      userQuery.trim() || undefined
    );
  };
  
  return (
    <div className="w-full p-4 border border-border bg-card shadow-sm">
      <div className="flex flex-col space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex-shrink min-w-0 pb-2 border-b border-border">
            <h2 className="text-xl font-avenir-pro-demi text-foreground">Analysis Controls</h2>
          </div>

          <div className="flex-1 min-w-[200px] flex items-center gap-2">
            <label className="text-xs font-avenir-pro-demi text-foreground flex-shrink-0">
              Analysis Type:
            </label>
            <Select value={analysisType} onValueChange={setAnalysisType} disabled={isLoading}>
              <SelectTrigger className="flex-1 h-8 py-1 px-3 border border-border rounded-md bg-background text-foreground font-avenir-pro focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring min-w-0 text-sm">
                <SelectValue placeholder="Select analysis type" />
              </SelectTrigger>
              <SelectContent className="font-avenir-pro bg-background">
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
                  "h-8 px-3 py-1 ml-2 flex-shrink-0 flex items-center font-avenir-pro text-xs",
                  advancedOptionsFilled && "bg-brand-caribbean-blue text-primary-foreground hover:bg-brand-caribbean-blue/90"
                )}
              >
                <Settings className="h-3.5 w-3.5 mr-1.5" />
                <span>Advanced Options</span>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[500px] p-4 border border-border bg-card shadow-md rounded-md mt-2" align="center" sideOffset={10}>
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
                    className="min-h-[100px] font-avenir-pro"
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
                    className="min-h-[100px] font-avenir-pro"
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
              onClick={handleRunAnalysis}
              disabled={isLoading}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              {isLoading ? 'Running Analysis...' : 'Run Analysis'}
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}; 