"use client";

interface HeaderProps {
  /** Toggle the mobile sidebar drawer. */
  onToggleSidebar: () => void;
  /** Reset chat to a fresh session. */
  onNewChat: () => void;
}

export default function Header({ onToggleSidebar, onNewChat }: HeaderProps) {
  return (
    <header className="relative flex h-14 shrink-0 items-center bg-primary px-3 sm:px-4">
      {/* Left: Hamburger (mobile only) */}
      <div className="flex w-10 shrink-0 lg:hidden">
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10"
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
      </div>

      {/* Center: App name — absolute centered on mobile, static on desktop */}
      <div className="absolute left-1/2 -translate-x-1/2 lg:static lg:translate-x-0">
        <span className="truncate text-sm font-bold tracking-tight text-white">
          <span className="opacity-80">&#10003;</span>{" "}
          Veris{" "}
          <span className="hidden font-normal text-white/60 sm:inline">|</span>{" "}
          <span className="hidden font-normal text-white/80 sm:inline">Clinical Intelligence</span>
        </span>
      </div>

      {/* Right: New Chat — icon-only on mobile, full button on sm+ */}
      <div className="ml-auto flex items-center gap-2">
        {/* <ThemeToggle /> — enable when dark mode is audited */}
        <button
          type="button"
          onClick={onNewChat}
          aria-label="New chat"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/20 text-white transition-colors hover:bg-white/10 sm:h-auto sm:w-auto sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs sm:font-medium"
        >
          <svg
            className="h-4 w-4 sm:h-3.5 sm:w-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
    </header>
  );
}
