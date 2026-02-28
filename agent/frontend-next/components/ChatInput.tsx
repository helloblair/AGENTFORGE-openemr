"use client";

import { useRef, useCallback, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resetHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, []);

  const submit = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const text = ta.value.trim();
    if (!text || isLoading) return;
    onSubmit(text);
    ta.value = "";
    ta.style.height = "auto";
  }, [onSubmit, isLoading]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  const handleFormSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      submit();
    },
    [submit],
  );

  return (
    <form
      onSubmit={handleFormSubmit}
      className="flex items-end gap-2 border-t border-border bg-surface p-4"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        disabled={isLoading}
        placeholder="Ask about a patient, medication, or clinical question..."
        onInput={resetHeight}
        onKeyDown={handleKeyDown}
        className="flex-1 resize-none rounded-lg border border-border bg-surface-secondary px-4 py-3 text-sm leading-relaxed text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={isLoading}
        aria-label="Send message"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? (
          <svg
            className="h-5 w-5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        ) : (
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        )}
      </button>
    </form>
  );
}
