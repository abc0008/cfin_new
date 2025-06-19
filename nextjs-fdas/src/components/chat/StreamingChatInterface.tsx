'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Message, Citation } from '@/types';
import { Loader2, Send, FileText, Zap } from 'lucide-react';
import { MessageRenderer } from './MessageRenderer';
import { FollowUpQuestions } from './FollowUpQuestions';
import { useStreamingChat } from '@/hooks/useStreamingChat';
import { 
  StreamingMessage, 
  ConnectionStatus, 
  VisualizationReadyIndicator 
} from '@/components/ui/streaming-indicators';
import { formatTimestamp } from '@/utils/formatters';

interface StreamingChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  activeDocuments?: string[];
  isLoading?: boolean;
  onCitationClick?: (citation: Citation) => void;
  onNavigateToHighlight?: (citation: Citation) => void;
  conversationId?: string;
  onMessageUpdate?: (message: Message) => void;
}

export function StreamingChatInterface({ 
  messages, 
  onSendMessage,
  activeDocuments = [],
  isLoading = false,
  onCitationClick,
  onNavigateToHighlight,
  conversationId,
  onMessageUpdate
}: StreamingChatInterfaceProps) {
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true); // Toggle for streaming mode
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Streaming chat hook
  const {
    isConnected,
    isStreaming,
    streamingText,
    streamingMessageId,
    toolsInProgress,
    completedVisualizations,
    sendStreamingMessage,
    sendStreamingMessageHTTP,
  } = useStreamingChat({
    conversationId: conversationId || '',
    onMessageUpdate: (message) => {
      console.log('Streaming message update:', message);
      // Pass the streaming message to the parent component
      onMessageUpdate?.(message);
    },
    onVisualizationReady: (type, data, index) => {
      console.log('Visualization ready:', type, data, index);
    },
    onError: (error) => {
      console.error('Streaming error:', error);
    }
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!inputValue.trim() || isSubmitting) return;
    
    try {
      setIsSubmitting(true);
      
      console.log(`Submit conditions: useStreaming=${useStreaming}, conversationId=${conversationId}, isConnected=${isConnected}`);
      
      if (useStreaming && conversationId && isConnected) {
        console.log('Using WebSocket streaming for message submission');
        // Add user message to chat immediately for streaming
        const userMessage: Message = {
          id: `user-${Date.now()}`,
          sessionId: conversationId,
          timestamp: new Date().toISOString(),
          role: 'user',
          content: inputValue,
          referencedDocuments: [],
          referencedAnalyses: [],
          citations: [],
          content_blocks: null,
          analysis_blocks: []
        };
        onMessageUpdate?.(userMessage);
        
        // Use streaming chat
        try {
          await sendStreamingMessage(inputValue);
        } catch (streamingError) {
          console.warn('WebSocket streaming failed, falling back to HTTP streaming:', streamingError);
          await sendStreamingMessageHTTP(inputValue);
        }
      } else {
        console.log('Falling back to HTTP submission - useStreaming:', useStreaming, 'conversationId:', conversationId, 'isConnected:', isConnected);
        // Fall back to traditional non-streaming approach
        await onSendMessage(inputValue);
      }
      
      setInputValue('');
      // Resize textarea to default height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  };

  const handleCitationClick = useCallback((citation: Citation) => {
    if (!activeDocuments) return;
    
    // Navigate to the citation in the document
    if (onNavigateToHighlight && citation.rects && citation.rects.length > 0) {
      onNavigateToHighlight(citation);
    }
  }, [activeDocuments, onNavigateToHighlight]);

  // Memoize the renderMessage function to prevent unnecessary re-renders
  const renderMessage = useCallback((message: Message, index: number) => {
    // Special case for loading message
    if (message.role === 'system' && message.content === 'AI is thinking...') {
      return (
        <div key={message.id} className="flex justify-start">
          <div className="max-w-[80%] rounded-lg px-4 py-2 bg-muted text-muted-foreground flex items-center">
            <Loader2 className="h-5 w-5 text-primary animate-spin mr-2" />
            <span className="font-avenir-pro">Analyzing document...</span>
          </div>
        </div>
      );
    }

    const isLastAssistantMessage = message.role === 'assistant' && 
      index === messages.length - 1 && 
      !isLoading && !isStreaming;

    return (
      <div key={`${message.id}-${message.role}`}>
        <div 
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
        >
          <div 
            className={`max-w-[80%] rounded-lg px-4 py-3 font-avenir-pro text-sm ${
              message.role === 'user' 
                ? 'bg-primary text-primary-foreground' 
                : message.role === 'system' 
                  ? 'bg-muted text-muted-foreground italic' 
                  : 'bg-card border border-border text-foreground shadow-sm'
            }`}
          >
            <MessageRenderer 
              message={message} 
              onCitationClick={handleCitationClick}
            />
            {/* Timestamp footnote */}
            <div className="text-xs opacity-50 mt-2 text-right">
              {formatTimestamp(message.timestamp)}
            </div>
          </div>
        </div>
        {/* Show follow-up questions after the last assistant message */}
        {isLastAssistantMessage && conversationId && (
          <FollowUpQuestions
            key={`followup-${message.id}`} // Force remount for each new message
            conversationId={conversationId}
            onQuestionClick={(question) => setInputValue(question)}
            disabled={isSubmitting || isLoading || isStreaming}
          />
        )}
      </div>
    );
  }, [handleCitationClick, messages.length, isLoading, isStreaming, conversationId, isSubmitting]);

  // Render streaming message if actively streaming
  const renderStreamingMessage = () => {
    if (!isStreaming || !streamingText) return null;

    return (
      <StreamingMessage 
        text={streamingText} 
        toolsInProgress={toolsInProgress} 
        showTypingIndicator={true}
      />
    );
  };

  return (
    <div className="flex flex-col h-full bg-background">
      <div className="py-1 px-2 border-b border-border bg-card">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-avenir-pro-demi text-foreground">Claude Assistant</h2>
          {conversationId && (
            <div className="flex items-center space-x-2">
              <ConnectionStatus isConnected={isConnected} isStreaming={isStreaming} />
              {useStreaming && !isConnected && (
                <span className="text-xs text-muted-foreground">Connecting...</span>
              )}
              <button
                onClick={() => setUseStreaming(!useStreaming)}
                className={`flex items-center px-2 py-1 rounded text-xs transition-colors ${
                  useStreaming 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                title={useStreaming ? 'Streaming enabled' : 'Streaming disabled'}
              >
                <Zap className="h-3 w-3 mr-1" />
                {useStreaming ? 'Live' : 'Standard'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-1 px-2 space-y-4 bg-muted/20 text-xs">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground p-6">
            <FileText className="h-12 w-12 mb-4 text-muted-foreground/40" />
            <h3 className="font-avenir-pro-demi text-base text-foreground mb-1">No messages yet</h3>
            <p className="mb-4 font-avenir-pro text-xs">Start a conversation by sending a message below.</p>
            
            <div className="text-sm text-left w-full max-w-md space-y-2 font-avenir-pro">
              <p className="font-avenir-pro-demi text-foreground">Try asking:</p>
              <button 
                onClick={() => setInputValue("What is the company's revenue for last quarter?")}
                className="p-1 bg-card border border-border rounded-md text-left w-full hover:bg-muted/30 transition-colors text-foreground text-xs"
              >
                What is the company's revenue for last quarter?
              </button>
              <button 
                onClick={() => setInputValue("Calculate the current ratio from the balance sheet.")}
                className="p-1 bg-card border border-border rounded-md text-left w-full hover:bg-muted/30 transition-colors text-foreground text-xs"
              >
                Calculate the current ratio from the balance sheet.
              </button>
              <button 
                onClick={() => setInputValue("How has the gross margin changed over time?")}
                className="p-1 bg-card border border-border rounded-md text-left w-full hover:bg-muted/30 transition-colors text-foreground text-xs"
              >
                How has the gross margin changed over time?
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => renderMessage(message, index))}
            {renderStreamingMessage()}
          </>
        )}
        {isLoading && !isStreaming && (
          <div className="flex justify-start">
            <div className="bg-card border border-border rounded-lg rounded-bl-none p-4 max-w-[80%] flex items-center shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin mr-2 text-primary" />
              <span className="text-sm text-muted-foreground font-avenir-pro">Claude is thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="py-1 px-2 border-t border-border bg-card">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                adjustTextareaHeight();
              }}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              className="fdas-textarea font-avenir-pro max-h-[150px] min-h-[44px] resize-none"
              disabled={isSubmitting || (isStreaming && useStreaming)}
            />
            {activeDocuments && activeDocuments.length > 0 && (
              <div className="absolute bottom-full mb-1 left-0 text-xs text-muted-foreground font-avenir-pro">
                <span className="bg-muted px-1 py-0.5 rounded">
                  Using {activeDocuments.length} document{activeDocuments.length !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || isSubmitting || (isStreaming && useStreaming) || (useStreaming && !isConnected)}
            className="bg-primary text-primary-foreground p-3 rounded-full hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed h-[44px] w-[44px] flex items-center justify-center transition-colors"
            title={useStreaming && !isConnected ? "Connecting to real-time chat..." : ""}
          >
            {isSubmitting || (isStreaming && useStreaming) ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}