"use client";

import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import { toast } from "sonner";
import type { Message, EhrContext } from "@/lib/types";
import { useKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ClinicalDisclaimer from "@/components/ClinicalDisclaimer";

function HomeContent() {
  const searchParams = useSearchParams();
  const isEmbedded = searchParams.get("embedded") === "true";

  const ehrContext: EhrContext | undefined = isEmbedded
    ? {
        patient_pid: searchParams.get("patient_pid") ?? "",
        encounter_id: searchParams.get("encounter_id") ?? "",
        ehr_user: searchParams.get("ehr_user") ?? "",
      }
    : undefined;

  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Generate threadId on the client only to avoid SSR/hydration mismatch
  useEffect(() => {
    setThreadId(uuidv4());
  }, []);

  const submitRef = useRef<((text: string) => void) | undefined>(undefined);
  const drawerRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);

  const handleReady = useCallback((submit: (text: string) => void) => {
    submitRef.current = submit;
  }, []);

  const handleExampleClick = useCallback((query: string) => {
    submitRef.current?.(query);
    // Move focus to the chat input after selecting an example
    requestAnimationFrame(() => chatInputRef.current?.focus());
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setThreadId(uuidv4());
    toast("New conversation started");
    // Focus the chat input after React re-renders
    requestAnimationFrame(() => chatInputRef.current?.focus());
  }, []);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(
    () => setSidebarOpen((prev) => !prev),
    [],
  );

  // Global keyboard shortcuts (Ctrl/Cmd+K, Escape)
  useKeyboardShortcuts({
    onNewChat: handleNewChat,
    onCloseSidebar: closeSidebar,
    sidebarOpen,
  });

  // Focus trap: keep Tab cycling inside the drawer when open
  useEffect(() => {
    if (!sidebarOpen) return;
    const drawer = drawerRef.current;
    if (!drawer) return;

    // Focus the drawer itself on open
    drawer.focus();

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = drawer.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleTab);
    return () => document.removeEventListener("keydown", handleTab);
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen flex-col">
      {/* Skip to main content link */}
      <a
        href="#main-chat"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:rounded focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to chat
      </a>

      {/* Header — hidden when embedded in OpenEMR iframe */}
      {!isEmbedded && (
        <Header onToggleSidebar={toggleSidebar} onNewChat={handleNewChat} />
      )}

      {/* Body: sidebar + chat area */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Desktop sidebar — hidden when embedded */}
        {!isEmbedded && (
          <nav aria-label="Sidebar navigation" className="hidden lg:block">
            <Sidebar
              threadId={threadId}
              messageCount={messages.length}
              onExampleClick={handleExampleClick}
            />
          </nav>
        )}

        {/* Mobile sidebar drawer — hidden when embedded */}
        {!isEmbedded && (
          <div
            className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? "" : "pointer-events-none"}`}
            aria-hidden={!sidebarOpen}
          >
            {/* Backdrop */}
            <div
              className="sidebar-backdrop absolute inset-0 bg-black/40"
              data-open={sidebarOpen}
              onClick={closeSidebar}
            />
            {/* Drawer */}
            <div
              ref={drawerRef}
              tabIndex={-1}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation sidebar"
              className="sidebar-drawer relative z-10 h-full w-[280px] shadow-xl outline-none"
              data-open={sidebarOpen}
            >
              <Sidebar
                threadId={threadId}
                messageCount={messages.length}
                onExampleClick={handleExampleClick}
                onClose={closeSidebar}
              />
            </div>
          </div>
        )}

        {/* Chat area */}
        <main id="main-chat" className="flex flex-1 flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            setMessages={setMessages}
            threadId={threadId}
            setThreadId={setThreadId}
            onReady={handleReady}
            chatInputRef={chatInputRef}
            ehrContext={ehrContext}
          />

          {/* Clinical disclaimer — hidden when embedded */}
          {!isEmbedded && (
            <footer>
              <ClinicalDisclaimer />
            </footer>
          )}
        </main>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={null}>
      <HomeContent />
    </Suspense>
  );
}
