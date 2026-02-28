"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessage, sendFeedback } from "@/lib/api";
import type { Message } from "@/lib/types";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState(() => uuidv4());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = useCallback(
    async (text: string) => {
      const userMessage: Message = { role: "user", content: text };
      setMessages((prev) => [...prev, userMessage]);
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
        const fallback = "Something went wrong. Please try again.";
        setError(err instanceof Error ? err.message : fallback);
      } finally {
        setIsLoading(false);
      }
    },
    [threadId],
  );

  const handleFeedback = useCallback(
    (traceId: string, vote: "up" | "down") => {
      // Optimistically update the message feedback state
      setMessages((prev) =>
        prev.map((msg) =>
          msg.trace_id === traceId ? { ...msg, feedback: vote } : msg,
        ),
      );

      // Fire-and-forget feedback to the API
      sendFeedback({ trace_id: traceId, score: vote === "up" ? 1 : 0 });
    },
    [],
  );

  return (
    <div className="flex h-full flex-col">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-neutral-400">
              Start a conversation with the OpenEMR Agent.
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

          {isLoading && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-neutral-100 px-4 py-3 dark:bg-neutral-800">
                <div className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="border-t border-red-200 bg-red-50 px-4 py-2 text-center text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Input */}
      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}
