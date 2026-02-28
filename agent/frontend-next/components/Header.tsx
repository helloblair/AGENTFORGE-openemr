"use client";

interface HeaderProps {
  /** Toggle the mobile sidebar drawer. */
  onToggleSidebar: () => void;
  /** Reset chat to a fresh session. */
  onNewChat: () => void;
}

export default function Header({ onToggleSidebar, onNewChat }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between bg-primary px-4">
      <div className="flex items-center gap-3">
        {/* Hamburger — mobile only */}
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10 lg:hidden"
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

        <span className="text-sm font-bold tracking-tight text-white">
          <span className="opacity-80">&#10003;</span>{" "}
          Veris{" "}
          <span className="font-normal text-white/60">|</span>{" "}
          <span className="font-normal text-white/80">Clinical Intelligence</span>
        </span>
      </div>

      <div className="flex items-center gap-2">
        {/* <ThemeToggle /> — enable when dark mode is audited */}
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-lg border border-white/20 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-white/10"
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
      </div>
    </header>
  );
}
