"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { sendMessage, sendFeedback, ApiError, TimeoutError } from "@/lib/api";
import type { Message, EhrContext } from "@/lib/types";
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
  /** Forwarded ref so the parent can focus the chat textarea. */
  chatInputRef?: React.RefObject<HTMLTextAreaElement | null>;
  /** EHR context from OpenEMR when embedded via iframe. */
  ehrContext?: EhrContext;
}

export default function ChatWindow({
  messages,
  setMessages,
  threadId,
  setThreadId,
  onReady,
  chatInputRef,
  ehrContext,
}: ChatWindowProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLLIElement>(null);
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

      // Prepend EHR context for the API call (invisible to the user)
      let apiMessage = text;
      if (ehrContext?.patient_pid) {
        const parts = [`patient_pid=${ehrContext.patient_pid}`];
        if (ehrContext.encounter_id) parts.push(`encounter_id=${ehrContext.encounter_id}`);
        if (ehrContext.ehr_user) parts.push(`ehr_user=${ehrContext.ehr_user}`);
        apiMessage = `[EHR Context: ${parts.join(", ")}] ${text}`;
      }

      try {
        const res = await sendMessage({ message: apiMessage, thread_id: threadId });

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
        let errorMessage: string;
        if (err instanceof TimeoutError) {
          errorMessage = "Request timed out. The agent may be processing a complex query.";
        } else if (err instanceof ApiError && err.status >= 500) {
          errorMessage = "The AI agent encountered an error. Please try again.";
        } else if (
          err instanceof TypeError ||
          (err instanceof Error && err.message === "Failed to fetch")
        ) {
          errorMessage = "Unable to reach the AI agent. Check your connection.";
        } else {
          errorMessage = err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.";
        }
        setError(errorMessage);
        toast.error("Failed to reach the AI agent");
      } finally {
        setIsLoading(false);
      }
    },
    [threadId, setMessages, setThreadId, ehrContext],
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
      sendFeedback({ trace_id: traceId, score: vote === "up" ? 1 : 0 }).catch(
        () => toast.error("Failed to submit feedback"),
      );
    },
    [setMessages],
  );

  // After a response arrives, return focus to the chat input
  useEffect(() => {
    if (!isLoading && chatInputRef?.current) {
      chatInputRef.current.focus();
    }
  }, [isLoading, chatInputRef]);

  return (
    <div className="flex h-full flex-col" aria-busy={isLoading}>
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-text-muted">
              Start a conversation with Veris.
            </p>
          </div>
        )}

        <ol
          role="log"
          aria-live="polite"
          aria-label="Chat messages"
          className="mx-auto flex max-w-3xl list-none flex-col gap-4 p-0"
        >
          {messages.map((msg, i) => (
            <li key={i}>
              <MessageBubble
                message={msg}
                onFeedback={handleFeedback}
              />
            </li>
          ))}

          {isLoading && (
            <li aria-label="Agent is thinking">
              <LoadingIndicator />
            </li>
          )}

          <li aria-hidden="true" ref={bottomRef} />
        </ol>
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
      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} textareaRef={chatInputRef} />
    </div>
  );
}
