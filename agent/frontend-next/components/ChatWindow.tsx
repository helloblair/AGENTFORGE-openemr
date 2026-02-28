"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { sendMessage, sendFeedback, ApiError, TimeoutError } from "@/lib/api";
import type { Message } from "@/lib/types";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";
import LoadingIndicator from "./LoadingIndicator";
import ErrorBanner from "./ErrorBanner";

interface ChatWindowProps {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  threadId: string;
  setThreadId: (id: string) => void;
  /** Called once on mount with the submit handler so the parent can trigger sends. */
  onReady?: (submit: (text: string) => void) => void;
}

export default function ChatWindow({
  messages,
  setMessages,
  threadId,
  setThreadId,
  onReady,
}: ChatWindowProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const lastUserMessageRef = useRef<string | null>(null);

  // Auto-scroll to bottom on new messages or loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = useCallback(
    async (text: string) => {
      const userMessage: Message = { role: "user", content: text };
      setMessages((prev) => [...prev, userMessage]);
      lastUserMessageRef.current = text;
      setIsLoading(true);
      setError(null);

      try {
        const res = await sendMessage({ message: text, thread_id: threadId });

        const assistantMessage: Message = {
          role: "assistant",
          content: res.response,
          tools_used: res.tools_used,
          confidence_score: res.confidence_score,
          trace_id: res.trace_id,
          requires_escalation: res.requires_escalation,
          feedback: null,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setThreadId(res.thread_id);
      } catch (err) {
        if (err instanceof TimeoutError) {
          setError(
            "Request timed out. The agent may be processing a complex query.",
          );
        } else if (err instanceof ApiError && err.status >= 500) {
          setError("The AI agent encountered an error. Please try again.");
        } else if (
          err instanceof TypeError ||
          (err instanceof Error && err.message === "Failed to fetch")
        ) {
          setError(
            "Unable to reach the AI agent. Check your connection.",
          );
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "Something went wrong. Please try again.",
          );
        }
      } finally {
        setIsLoading(false);
      }
    },
    [threadId, setMessages, setThreadId],
  );

  const handleRetry = useCallback(() => {
    const lastMsg = lastUserMessageRef.current;
    if (!lastMsg) return;
    // Remove the last user message so handleSubmit re-adds it
    setMessages((prev) => {
      const idx = prev.findLastIndex(
        (m) => m.role === "user" && m.content === lastMsg,
      );
      if (idx === -1) return prev;
      return [...prev.slice(0, idx), ...prev.slice(idx + 1)];
    });
    setError(null);
    handleSubmit(lastMsg);
  }, [handleSubmit, setMessages]);

  // Expose submit to parent via stable ref
  const submitRef = useRef(handleSubmit);
  submitRef.current = handleSubmit;

  useEffect(() => {
    onReady?.((text: string) => submitRef.current(text));
  }, [onReady]);

  const handleFeedback = useCallback(
    (traceId: string, vote: "up" | "down") => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.trace_id === traceId ? { ...msg, feedback: vote } : msg,
        ),
      );
      sendFeedback({ trace_id: traceId, score: vote === "up" ? 1 : 0 });
    },
    [setMessages],
  );

  return (
    <div className="flex h-full flex-col">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-text-muted">
              Start a conversation with Veris.
            </p>
          </div>
        )}

        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              message={msg}
              onFeedback={handleFeedback}
            />
          ))}

          {isLoading && <LoadingIndicator />}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={handleRetry}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Input */}
      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}
