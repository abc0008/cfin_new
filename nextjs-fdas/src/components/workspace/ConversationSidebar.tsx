'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  History,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import {
  conversationsApi,
  ConversationSummary,
} from '@/lib/api/conversations';

interface ConversationSidebarProps {
  currentSessionId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  /** Bump this number to force a refresh of the list (e.g., after first message). */
  refreshKey?: number;
}

const COLLAPSE_STORAGE_KEY = 'cfin:sidebarCollapsed';

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function ConversationSidebar({
  currentSessionId,
  onSelectConversation,
  onNewConversation,
  refreshKey = 0,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Restore collapse preference
  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === '1');
    } catch {
      /* no-op */
    }
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      try {
        window.localStorage.setItem(COLLAPSE_STORAGE_KEY, prev ? '0' : '1');
      } catch {
        /* no-op */
      }
      return !prev;
    });
  };

  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await conversationsApi.listRecentConversations(50);
      setConversations(items);
    } catch (err) {
      console.error('[ConversationSidebar] Failed to load conversations:', err);
      setError('Could not load history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations, refreshKey, currentSessionId]);

  const handleDelete = async (event: React.MouseEvent, conversationId: string) => {
    event.stopPropagation();
    if (!window.confirm('Delete this conversation? This cannot be undone.')) return;
    setDeletingId(conversationId);
    try {
      await conversationsApi.deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (conversationId === currentSessionId) {
        onNewConversation();
      }
    } catch (err) {
      console.error('[ConversationSidebar] Failed to delete conversation:', err);
    } finally {
      setDeletingId(null);
    }
  };

  if (collapsed) {
    return (
      <div className="workspace-panel flex w-12 flex-shrink-0 flex-col items-center gap-2 overflow-hidden py-3">
        <button
          onClick={toggleCollapsed}
          className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
          title="Expand session history"
          aria-label="Expand session history"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          onClick={onNewConversation}
          className="rounded-md p-2 text-primary transition-colors hover:bg-primary/10"
          title="New conversation"
          aria-label="New conversation"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>
        <div className="mt-1 rounded-md p-2 text-muted-foreground" title="Session history">
          <History className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-panel flex w-64 flex-shrink-0 flex-col overflow-hidden">
      <div className="workspace-panel-bar flex flex-shrink-0 items-center justify-between px-3 py-3">
        <h2 className="flex items-center text-sm font-avenir-pro-demi text-foreground">
          <History className="mr-2 h-4 w-4 text-primary" />
          Sessions
        </h2>
        <div className="flex items-center gap-1">
          <button
            onClick={loadConversations}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
            title="Refresh history"
            aria-label="Refresh history"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={toggleCollapsed}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
            title="Collapse session history"
            aria-label="Collapse session history"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-shrink-0 px-3 pt-3">
        <button
          onClick={onNewConversation}
          className="workspace-primary-btn flex w-full items-center justify-center text-xs"
          data-testid="new-conversation-btn"
        >
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          New Conversation
        </button>
      </div>

      <div className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pb-3" data-testid="conversation-list">
        {loading && conversations.length === 0 && (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            <span className="text-xs">Loading sessions…</span>
          </div>
        )}

        {error && (
          <div className="px-2 py-4 text-center text-xs text-destructive">{error}</div>
        )}

        {!loading && !error && conversations.length === 0 && (
          <div className="px-2 py-6 text-center text-xs text-muted-foreground">
            No previous sessions yet. Your analysis conversations will appear here.
          </div>
        )}

        {conversations.map((conversation) => {
          const isActive = conversation.id === currentSessionId;
          return (
            <button
              key={conversation.id}
              onClick={() => onSelectConversation(conversation.id)}
              data-testid="conversation-item"
              data-conversation-id={conversation.id}
              className={`group relative w-full rounded-lg px-2.5 py-2 text-left transition-colors ${
                isActive
                  ? 'bg-primary/10 ring-1 ring-primary/40'
                  : 'hover:bg-muted/40'
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <span
                  className={`line-clamp-2 break-words text-xs font-avenir-pro-demi leading-snug ${
                    isActive ? 'text-primary' : 'text-foreground'
                  }`}
                >
                  {conversation.title || 'Untitled conversation'}
                </span>
                <span
                  onClick={(e) => handleDelete(e, conversation.id)}
                  role="button"
                  aria-label="Delete conversation"
                  className="invisible flex-shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive group-hover:visible"
                >
                  {deletingId === conversation.id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                </span>
              </div>

              {conversation.lastMessage?.content && (
                <p className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">
                  {conversation.lastMessage.content}
                </p>
              )}

              <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                <span>{relativeTime(conversation.updatedAt)}</span>
                {conversation.documentCount > 0 && (
                  <span className="inline-flex items-center gap-0.5">
                    <FileText className="h-3 w-3" />
                    {conversation.documentCount}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ConversationSidebar;
