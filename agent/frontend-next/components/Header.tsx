"use client";

interface HeaderProps {
  /** Toggle the mobile sidebar drawer. */
  onToggleSidebar: () => void;
  /** Reset chat to a fresh session. */
  onNewChat: () => void;
}

export default function Header({ onToggleSidebar, onNewChat }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-4 dark:border-neutral-800 dark:bg-neutral-950">
      <div className="flex items-center gap-3">
        {/* Hamburger — mobile only */}
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-neutral-600 transition-colors hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800 lg:hidden"
        >
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>

        <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          OpenEMR Agent
        </span>
      </div>

      <button
        type="button"
        onClick={onNewChat}
        className="flex items-center gap-1.5 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
      >
        <svg
          className="h-3.5 w-3.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
        New Chat
      </button>
    </header>
  );
}
