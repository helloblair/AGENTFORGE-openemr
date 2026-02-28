"use client";

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { checkHealth } from "@/lib/api";

const EXAMPLE_QUERIES = [
  "Look up patient John Smith",
  "What medications is patient Jane Doe taking?",
  "Check for drug interactions between lisinopril and potassium",
  "Who is the primary care provider for patient ID xyz?",
  "What allergies does patient Sarah Johnson have?",
];

interface SidebarProps {
  threadId: string;
  messageCount: number;
  onExampleClick: (query: string) => void;
  /** Called when an action inside the sidebar should close the mobile drawer. */
  onClose?: () => void;
}

export default function Sidebar({
  threadId,
  messageCount,
  onExampleClick,
  onClose,
}: SidebarProps) {
  const [apiStatus, setApiStatus] = useState<"connected" | "unreachable">(
    "unreachable",
  );
  const [openemrConnected, setOpenemrConnected] = useState(false);
  const prevApiStatus = useRef<"connected" | "unreachable" | null>(null);

  useEffect(() => {
    let active = true;

    async function poll() {
      const health = await checkHealth();
      if (!active) return;
      const newStatus = health.status === "unreachable" ? "unreachable" : "connected" as const;

      // Toast only when transitioning from connected → unreachable
      if (prevApiStatus.current === "connected" && newStatus === "unreachable") {
        toast.warning("API connection lost");
      }
      prevApiStatus.current = newStatus;

      setApiStatus(newStatus);
      setOpenemrConnected(health.openemr_connected);
    }

    poll();
    const interval = setInterval(poll, 30_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  function handleExampleClick(query: string) {
    onExampleClick(query);
    onClose?.();
  }

  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-border bg-surface-secondary">
      {/* Sidebar header */}
      <div className="border-b border-border px-5 py-5">
        <h2 className="text-lg font-bold text-text-primary">
          Veris
        </h2>
        <p className="mt-0.5 text-xs text-text-secondary">
          Clinical Intelligence Assistant
        </p>
      </div>

      {/* Example queries */}
      <nav aria-label="Example queries" className="flex-1 overflow-y-auto px-4 py-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-text-secondary">
          Try asking&hellip;
        </p>
        <div className="flex flex-col gap-2">
          {EXAMPLE_QUERIES.map((query) => (
            <button
              key={query}
              type="button"
              onClick={() => handleExampleClick(query)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-left text-sm text-text-primary transition-colors hover:border-primary/40 hover:bg-secondary"
            >
              {query}
            </button>
          ))}
        </div>
      </nav>

      {/* Session info + health + footer */}
      <div className="border-t border-border px-4 py-4">
        {/* Session info */}
        <div className="mb-3 space-y-1 text-xs text-text-secondary">
          <p>
            Session ID:{" "}
            <span className="font-mono">{threadId.slice(0, 8)}&hellip;</span>
          </p>
          <p>Messages: {messageCount}</p>
        </div>

        {/* Health status */}
        <div className="mb-3 space-y-1.5" role="status" aria-label="System health">
          <div className="flex items-center gap-2 text-xs">
            <span
              aria-hidden="true"
              className={`inline-block h-2 w-2 rounded-full ${
                apiStatus === "connected" ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <span className="text-text-secondary">
              {apiStatus === "connected" ? "API Connected" : "API Unreachable"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span
              aria-hidden="true"
              className={`inline-block h-2 w-2 rounded-full ${
                openemrConnected ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <span className="text-text-secondary">
              {openemrConnected ? "OpenEMR Connected" : "OpenEMR Unreachable"}
            </span>
          </div>
        </div>

        {/* Keyboard shortcuts */}
        <div className="mb-3">
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-text-secondary">
            Shortcuts
          </p>
          <div className="space-y-1 text-[11px] text-text-muted">
            <p>
              <kbd className="rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px]">Ctrl</kbd>
              {" + "}
              <kbd className="rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px]">K</kbd>
              <span className="ml-1.5">&mdash; New chat</span>
            </p>
            <p>
              <kbd className="rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px]">Enter</kbd>
              <span className="ml-1.5">&mdash; Send message</span>
            </p>
            <p>
              <kbd className="rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px]">Shift</kbd>
              {" + "}
              <kbd className="rounded border border-border bg-surface px-1 py-0.5 font-mono text-[10px]">Enter</kbd>
              <span className="ml-1.5">&mdash; New line</span>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-[10px] text-text-muted">
          Powered by OpenEMR + Claude
        </p>
      </div>
    </aside>
  );
}
