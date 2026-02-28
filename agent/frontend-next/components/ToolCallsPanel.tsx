"use client";

interface ToolCallsPanelProps {
  tools: string[];
}

export default function ToolCallsPanel({ tools }: ToolCallsPanelProps) {
  return (
    <details className="mt-3 group">
      <summary className="flex cursor-pointer select-none items-center gap-1.5 text-[12px] font-medium text-neutral-500 dark:text-neutral-400">
        {/* Chevron rotates when open */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-3.5 w-3.5 shrink-0 transition-transform group-open:rotate-90"
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        Tools called ({tools.length})
      </summary>

      <div className="mt-2 flex flex-wrap gap-1.5 pl-5">
        {tools.map((tool) => (
          <span
            key={tool}
            className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] text-slate-700 dark:bg-slate-700 dark:text-slate-300"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {tool}
          </span>
        ))}
      </div>
    </details>
  );
}
