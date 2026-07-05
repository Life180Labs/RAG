'use client';

import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDocument } from '@/hooks/use-documents';
import {
  useConversationMemory,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useMessages,
  useSendMessage,
  useUpdateConversationMemory,
} from '@/hooks/use-conversations';
import { ApiRequestError } from '@/services/api-client';
import { exportConversationMarkdown } from '@/services/conversation-service';

export function ChatPanel({
  documentId,
  vectorIndexId,
}: {
  documentId: string;
  vectorIndexId: string;
}) {
  const { data: document } = useDocument(documentId);
  const repositoryId = document?.repository_id ?? null;

  const { data: conversations, isLoading: conversationsLoading } = useConversations(
    documentId,
    vectorIndexId,
  );
  const createConversation = useCreateConversation(documentId, vectorIndexId);
  const deleteConversation = useDeleteConversation(documentId, vectorIndexId);

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [exportedText, setExportedText] = useState<string | null>(null);

  const { data: messages, isLoading: messagesLoading } = useMessages(
    documentId,
    vectorIndexId,
    activeConversationId,
  );
  const sendMessage = useSendMessage(documentId, vectorIndexId, activeConversationId ?? '');

  const { data: memory } = useConversationMemory(repositoryId);
  const updateMemory = useUpdateConversationMemory(repositoryId ?? '');
  // null = user hasn't edited yet; display falls back to the loaded memory value.
  const [customInstructionsDraft, setCustomInstructionsDraft] = useState<string | null>(null);
  const customInstructions = customInstructionsDraft ?? memory?.custom_instructions ?? '';

  const activeConversation = conversations?.find((c) => c.id === activeConversationId) ?? null;

  async function handleCreateConversation() {
    setError(null);
    try {
      const response = await createConversation.mutateAsync({
        title: newTitle.trim() || undefined,
      });
      setActiveConversationId(response.data.id);
      setNewTitle('');
      setShowNewForm(false);
      setExportedText(null);
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : 'Unable to start a new conversation.',
      );
    }
  }

  async function handleDelete(conversationId: string) {
    setError(null);
    try {
      await deleteConversation.mutateAsync(conversationId);
      if (activeConversationId === conversationId) {
        setActiveConversationId(null);
        setExportedText(null);
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to delete conversation.');
    }
  }

  async function handleSend() {
    if (!activeConversationId || !messageInput.trim()) return;
    setError(null);
    const content = messageInput;
    setMessageInput('');
    try {
      await sendMessage.mutateAsync({ content });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to send message.');
    }
  }

  async function handleExport() {
    if (!activeConversationId) return;
    setError(null);
    try {
      const text = await exportConversationMarkdown(
        documentId,
        vectorIndexId,
        activeConversationId,
      );
      setExportedText(text);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to export conversation.');
    }
  }

  async function handleSaveMemory() {
    setError(null);
    try {
      await updateMemory.mutateAsync({ custom_instructions: customInstructions.trim() || null });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to save memory.');
    }
  }

  return (
    <div className="border-border space-y-3 border-t pt-2 pl-4" data-testid="chat-panel">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-xs font-medium">Conversations</p>
        <div className="flex items-center gap-2">
          {!showNewForm && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowNewForm(true)}
              data-testid="chat-new-conversation-button"
            >
              New conversation
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowMemory((prev) => !prev)}
            data-testid="chat-memory-toggle"
          >
            {showMemory ? 'Hide memory' : 'Memory'}
          </Button>
        </div>
      </div>

      {showNewForm && (
        <div
          className="border-border flex items-center gap-2 rounded-lg border p-2"
          data-testid="chat-new-conversation-form"
        >
          <input
            className="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-sm"
            placeholder="Conversation title (optional)"
            value={newTitle}
            onChange={(event) => setNewTitle(event.target.value)}
            data-testid="chat-new-conversation-title-input"
          />
          <Button
            size="sm"
            onClick={handleCreateConversation}
            disabled={createConversation.isPending}
            data-testid="chat-new-conversation-confirm-button"
          >
            {createConversation.isPending ? 'Starting…' : 'Start'}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setShowNewForm(false)}>
            Cancel
          </Button>
        </div>
      )}

      {showMemory && (
        <div
          className="border-border space-y-2 rounded-lg border p-2"
          data-testid="chat-memory-panel"
        >
          <p className="text-muted-foreground text-xs">
            Custom instructions applied to every conversation you have in this repository.
          </p>
          <textarea
            className="border-input min-h-[60px] w-full rounded-lg border bg-transparent px-2 py-1 text-sm"
            placeholder="e.g. Always answer in bullet points."
            value={customInstructions}
            onChange={(event) => setCustomInstructionsDraft(event.target.value)}
            data-testid="chat-memory-instructions-input"
          />
          <Button
            size="sm"
            onClick={handleSaveMemory}
            disabled={updateMemory.isPending || !repositoryId}
            data-testid="chat-memory-save-button"
          >
            {updateMemory.isPending ? 'Saving…' : 'Save instructions'}
          </Button>
          {memory?.preferences && Object.keys(memory.preferences).length > 0 && (
            <pre
              className="border-border bg-muted/40 max-h-32 overflow-auto rounded-lg border p-2 text-xs"
              data-testid="chat-memory-preferences"
            >
              {JSON.stringify(memory.preferences, null, 2)}
            </pre>
          )}
        </div>
      )}

      {conversationsLoading && <Skeleton className="h-8 w-full" />}

      {conversations && conversations.length > 0 && (
        <ul className="divide-border divide-y text-xs" data-testid="chat-session-switcher">
          {conversations.map((conversation) => (
            <li key={conversation.id} className="flex items-center justify-between gap-2 py-1">
              <button
                type="button"
                className="flex-1 truncate text-left"
                onClick={() => {
                  setActiveConversationId(conversation.id);
                  setExportedText(null);
                }}
                data-testid={`chat-conversation-item-${conversation.id}`}
              >
                <Badge variant={activeConversationId === conversation.id ? 'default' : 'secondary'}>
                  {conversation.title || 'Untitled conversation'}
                </Badge>
                <span className="text-muted-foreground ml-2">
                  {conversation.total_tokens} tokens
                </span>
              </button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleDelete(conversation.id)}
                data-testid={`chat-conversation-delete-${conversation.id}`}
              >
                Delete
              </Button>
            </li>
          ))}
        </ul>
      )}

      {activeConversation && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium" data-testid="chat-active-conversation-title">
              {activeConversation.title || 'Untitled conversation'}
            </p>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleExport}
              data-testid="chat-export-button"
            >
              Export
            </Button>
          </div>

          {messagesLoading && <Skeleton className="h-24 w-full" />}

          <div
            className="border-border max-h-96 space-y-2 overflow-auto rounded-lg border p-2"
            data-testid="chat-message-list"
          >
            {messages && messages.length === 0 && (
              <p className="text-muted-foreground text-xs">
                No messages yet. Say hello to get started.
              </p>
            )}
            {messages?.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === 'user'
                    ? 'bg-primary/10 ml-auto max-w-[85%] rounded-lg p-2 text-sm'
                    : 'bg-muted/40 mr-auto max-w-[85%] rounded-lg p-2 text-sm'
                }
                data-testid={`chat-message-${message.role}`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <p className="text-muted-foreground mt-1 text-[10px]">
                  {message.role} · {message.token_count} tokens
                </p>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <textarea
              className="border-input min-h-[40px] w-full rounded-lg border bg-transparent px-2 py-1 text-sm"
              placeholder="Ask a follow-up question…"
              value={messageInput}
              onChange={(event) => setMessageInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  handleSend();
                }
              }}
              data-testid="chat-message-input"
            />
            <Button
              size="sm"
              onClick={handleSend}
              disabled={sendMessage.isPending || !messageInput.trim()}
              data-testid="chat-send-button"
            >
              {sendMessage.isPending ? 'Thinking…' : 'Send'}
            </Button>
          </div>

          {exportedText && (
            <pre
              className="border-border bg-muted/40 max-h-64 overflow-auto rounded-lg border p-2 text-xs whitespace-pre-wrap"
              data-testid="chat-export-output"
            >
              {exportedText}
            </pre>
          )}
        </div>
      )}

      {!activeConversation && conversations && conversations.length === 0 && !showNewForm && (
        <p className="text-muted-foreground text-xs">
          No conversations yet for this index. Start one to chat with your documents.
        </p>
      )}
    </div>
  );
}
