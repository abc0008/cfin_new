'use client';

import React, { useState, useEffect } from 'react';
import { Loader2, ChevronRight } from 'lucide-react';
import { conversationApi } from '@/lib/api/conversation';

interface FollowUpQuestionsProps {
  conversationId: string;
  onQuestionClick: (question: string) => void;
  disabled?: boolean;
  seedKey?: string;
}

const inFlightFollowUpRequests = new Map<string, Promise<string[]>>();
const resolvedFollowUpResults = new Map<string, string[]>();

export function FollowUpQuestions({ 
  conversationId, 
  onQuestionClick, 
  disabled = false,
  seedKey = 'default'
}: FollowUpQuestionsProps) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasGenerated, setHasGenerated] = useState(false);

  useEffect(() => {
    if (conversationId && !hasGenerated && !disabled) {
      generateQuestions();
    }
  }, [conversationId, hasGenerated, disabled, seedKey]);

  const generateQuestions = async () => {
    if (!conversationId || isLoading) return;

    const cacheKey = `${conversationId}:${seedKey}:3`;

    try {
      setIsLoading(true);

      const cached = resolvedFollowUpResults.get(cacheKey);
      if (cached && cached.length > 0) {
        setQuestions(cached);
        setHasGenerated(true);
        return;
      }

      let request = inFlightFollowUpRequests.get(cacheKey);
      if (!request) {
        request = conversationApi.generateFollowUpQuestions(conversationId, 3);
        inFlightFollowUpRequests.set(cacheKey, request);
      }

      const generatedQuestions = await request;
      inFlightFollowUpRequests.delete(cacheKey);
      resolvedFollowUpResults.set(cacheKey, generatedQuestions);
      if (resolvedFollowUpResults.size > 100) {
        const first = resolvedFollowUpResults.keys().next().value as string | undefined;
        if (first) {
          resolvedFollowUpResults.delete(first);
        }
      }
      setQuestions(generatedQuestions);
      setHasGenerated(true);
    } catch (error) {
      inFlightFollowUpRequests.delete(cacheKey);
      console.error('Failed to generate follow-up questions:', error);
      // Set default questions as fallback
      setQuestions([
        "What trends do you see in the financial performance?",
        "How does this compare to industry benchmarks?",
        "What are the key risk factors to consider?"
      ]);
      setHasGenerated(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuestionClick = (question: string) => {
    if (disabled) return;
    onQuestionClick(question);
  };

  // Don't render if disabled or no conversation ID
  if (disabled || !conversationId) {
    return null;
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin mr-2" />
        <span className="font-avenir-pro">Generating follow-up questions...</span>
      </div>
    );
  }

  // Don't render if no questions
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="px-2 py-2 border-t border-border bg-card/50">
      <div className="text-xs font-avenir-pro-demi text-foreground mb-2">
        Follow-up questions:
      </div>
      <div className="space-y-1">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => handleQuestionClick(question)}
            disabled={disabled}
            className="group w-full text-left p-2 text-xs bg-background hover:bg-muted/30 rounded-md border border-border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center justify-between">
              <span className="font-avenir-pro text-foreground group-hover:text-primary transition-colors">
                {question}
              </span>
              <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:text-primary transition-colors opacity-0 group-hover:opacity-100" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
