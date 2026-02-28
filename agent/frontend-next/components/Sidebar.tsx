"use client";

import { useState, useEffect } from "react";
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

  useEffect(() => {
    let active = true;

    async function poll() {
      const health = await checkHealth();
      if (!active) return;
      setApiStatus(health.status === "unreachable" ? "unreachable" : "connected");
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
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900">
      {/* Sidebar header */}
      <div className="border-b border-neutral-200 px-5 py-5 dark:border-neutral-800">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          OpenEMR AI Agent
        </h2>
        <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
          Clinical Intelligence Assistant
        </p>
      </div>

      {/* Example queries */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
          Try asking&hellip;
        </p>
        <div className="flex flex-col gap-2">
          {EXAMPLE_QUERIES.map((query) => (
            <button
              key={query}
              type="button"
              onClick={() => handleExampleClick(query)}
              className="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-left text-sm text-neutral-700 transition-colors hover:border-blue-300 hover:bg-blue-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:border-blue-600 dark:hover:bg-blue-950"
            >
              {query}
            </button>
          ))}
        </div>
      </div>

      {/* Session info + health + footer */}
      <div className="border-t border-neutral-200 px-4 py-4 dark:border-neutral-800">
        {/* Session info */}
        <div className="mb-3 space-y-1 text-xs text-neutral-500 dark:text-neutral-400">
          <p>
            Session ID:{" "}
            <span className="font-mono">{threadId.slice(0, 8)}&hellip;</span>
          </p>
          <p>Messages: {messageCount}</p>
        </div>

        {/* Health status */}
        <div className="mb-3 space-y-1.5">
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                apiStatus === "connected" ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-neutral-600 dark:text-neutral-400">
              {apiStatus === "connected" ? "API Connected" : "API Unreachable"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                openemrConnected ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-neutral-600 dark:text-neutral-400">
              {openemrConnected ? "OpenEMR Connected" : "OpenEMR Unreachable"}
            </span>
          </div>
        </div>

        {/* Footer */}
        <p className="text-[10px] text-neutral-400 dark:text-neutral-500">
          Powered by OpenEMR + Claude
        </p>
      </div>
    </aside>
  );
}
