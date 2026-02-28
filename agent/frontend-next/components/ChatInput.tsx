"use client";

import { useRef, useCallback, useEffect, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
}

// Max height ≈ 4 lines of text (~24px line-height × 4 + padding)
const MAX_HEIGHT = 120;

export default function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resetHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, MAX_HEIGHT)}px`;
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

  // Mobile keyboard: scroll input into view when focused
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const handleFocus = () => {
      // Small delay lets the virtual keyboard finish opening
      setTimeout(() => {
        ta.scrollIntoView({ behavior: "smooth", block: "end" });
      }, 300);
    };
    ta.addEventListener("focus", handleFocus);
    return () => ta.removeEventListener("focus", handleFocus);
  }, []);

  return (
    <form
      onSubmit={handleFormSubmit}
      className="border-t border-border bg-surface px-2 py-2 sm:px-4 sm:py-3"
    >
      {/* Relative wrapper so the send button can sit inside the textarea area */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={1}
          disabled={isLoading}
          placeholder="Ask about a patient, medication, or clinical question..."
          onInput={resetHeight}
          onKeyDown={handleKeyDown}
          className="w-full resize-none rounded-xl border border-border bg-surface-secondary py-3 pl-4 pr-12 text-sm leading-relaxed text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading}
          aria-label="Send message"
          className="absolute bottom-1.5 right-1.5 flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? (
            <svg
              className="h-4 w-4 animate-spin"
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
              className="h-4 w-4"
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
      </div>
    </form>
  );
}
