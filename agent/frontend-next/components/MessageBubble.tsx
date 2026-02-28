"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "@/lib/types";
import ToolCallsPanel from "./ToolCallsPanel";
import ConfidenceBar from "./ConfidenceBar";
import EscalationWarning from "./EscalationWarning";
import FeedbackButtons from "./FeedbackButtons";
import CopyButton from "./CopyButton";

// ── Markdown component overrides ─────────────────────────────────────────────

const markdownComponents: Components = {
  code({ className, children, ...rest }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded bg-secondary px-1 py-0.5 font-mono text-[13px]"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className={`block overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-[13px] leading-relaxed text-slate-100 ${className ?? ""}`}
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

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} ${isUser ? "animate-message-in-right" : "animate-message-in-left"}`}>
      <div
        className={`relative rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "max-w-[85%] bg-primary text-white sm:max-w-[75%] md:max-w-[70%]"
            : "group max-w-full bg-surface-secondary text-text-primary sm:max-w-[85%] md:max-w-[80%]"
        }`}
      >
        {/* Copy button — assistant messages only */}
        {!isUser && <CopyButton text={message.content} />}
        {/* Role indicator */}
        <div
          className={`mb-1 text-[10px] font-medium sm:text-[11px] ${
            isUser
              ? "text-white/60"
              : "text-text-muted"
          }`}
        >
          {isUser ? "You" : "Veris"}
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

            {message.trace_id && (
              <FeedbackButtons
                traceId={message.trace_id}
                currentFeedback={message.feedback ?? null}
                onFeedback={onFeedback ?? (() => {})}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
