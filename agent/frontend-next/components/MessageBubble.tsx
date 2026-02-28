"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "@/lib/types";
import ToolCallsPanel from "./ToolCallsPanel";
import ConfidenceBar from "./ConfidenceBar";
import EscalationWarning from "./EscalationWarning";

// ── Sub-components ───────────────────────────────────────────────────────────

function FeedbackButtons({
  current,
  onFeedback,
}: {
  current: "up" | "down" | null | undefined;
  onFeedback: (vote: "up" | "down") => void;
}) {
  return (
    <div className="mt-2 flex items-center gap-1">
      <button
        type="button"
        onClick={() => onFeedback("up")}
        aria-label="Thumbs up"
        className={`rounded p-1 transition-colors ${
          current === "up"
            ? "text-green-600 dark:text-green-400"
            : "text-neutral-400 hover:text-green-600 dark:hover:text-green-400"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
        >
          <path d="M1 8.25a1.25 1.25 0 112.5 0v7.5a1.25 1.25 0 11-2.5 0v-7.5zM6 7.082V15.5a1.5 1.5 0 001.5 1.5h6.269a1.5 1.5 0 001.471-1.206l1.413-7.07A1.5 1.5 0 0015.182 7H11.5V3.5a2 2 0 00-2-2h-.172a1 1 0 00-.95.684L6 7.082z" />
        </svg>
      </button>
      <button
        type="button"
        onClick={() => onFeedback("down")}
        aria-label="Thumbs down"
        className={`rounded p-1 transition-colors ${
          current === "down"
            ? "text-red-600 dark:text-red-400"
            : "text-neutral-400 hover:text-red-600 dark:hover:text-red-400"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
        >
          <path d="M19 11.75a1.25 1.25 0 10-2.5 0v-7.5a1.25 1.25 0 102.5 0v7.5zM14 12.918V4.5A1.5 1.5 0 0012.5 3H6.231a1.5 1.5 0 00-1.471 1.206l-1.413 7.07A1.5 1.5 0 004.818 13H8.5v3.5a2 2 0 002 2h.172a1 1 0 00.95-.684L14 12.918z" />
        </svg>
      </button>
    </div>
  );
}

// ── Markdown component overrides ─────────────────────────────────────────────

const markdownComponents: Components = {
  code({ className, children, ...rest }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded bg-neutral-200 px-1 py-0.5 font-mono text-[13px] dark:bg-neutral-700"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className={`block overflow-x-auto rounded-lg bg-neutral-900 p-3 font-mono text-[13px] leading-relaxed text-neutral-100 dark:bg-neutral-950 ${className ?? ""}`}
        {...rest}
      >
        {children}
      </code>
    );
  },
  pre({ children }) {
    return <pre className="my-2">{children}</pre>;
  },
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="mb-2 ml-4 list-disc last:mb-0">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="mb-2 ml-4 list-decimal last:mb-0">{children}</ol>;
  },
  li({ children }) {
    return <li className="mb-0.5">{children}</li>;
  },
  strong({ children }) {
    return <strong className="font-semibold">{children}</strong>;
  },
};

// ── MessageBubble ────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: Message;
  onFeedback?: (traceId: string, score: "up" | "down") => void;
}

export default function MessageBubble({
  message,
  onFeedback,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  const handleVote = (vote: "up" | "down") => {
    if (message.trace_id && onFeedback) {
      onFeedback(message.trace_id, vote);
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
        }`}
      >
        {/* Role indicator */}
        <div
          className={`mb-1 text-[11px] font-medium ${
            isUser
              ? "text-blue-200"
              : "text-neutral-400 dark:text-neutral-500"
          }`}
        >
          {isUser ? "You" : "Agent"}
        </div>

        {/* Content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Assistant-only metadata */}
        {!isUser && (
          <>
            {message.tools_used && message.tools_used.length > 0 && (
              <ToolCallsPanel tools={message.tools_used} />
            )}

            {message.confidence_score != null && (
              <ConfidenceBar score={message.confidence_score} />
            )}

            {message.requires_escalation && <EscalationWarning />}

            <FeedbackButtons current={message.feedback} onFeedback={handleVote} />
          </>
        )}
      </div>
    </div>
  );
}
