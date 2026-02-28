"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { toast } from "sonner";
import type { Message } from "@/lib/types";
import { useKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ClinicalDisclaimer from "@/components/ClinicalDisclaimer";

export default function Home() {
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
      {/* Header — always visible */}
      <Header onToggleSidebar={toggleSidebar} onNewChat={handleNewChat} />

      {/* Body: sidebar + chat area */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Desktop sidebar — always visible at lg+ */}
        <div className="hidden lg:block">
          <Sidebar
            threadId={threadId}
            messageCount={messages.length}
            onExampleClick={handleExampleClick}
          />
        </div>

        {/* Mobile sidebar drawer — CSS-transitioned slide + backdrop */}
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

        {/* Chat area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            setMessages={setMessages}
            threadId={threadId}
            setThreadId={setThreadId}
            onReady={handleReady}
            chatInputRef={chatInputRef}
          />

          {/* Clinical disclaimer */}
          <ClinicalDisclaimer />
        </div>
      </div>
    </div>
  );
}
