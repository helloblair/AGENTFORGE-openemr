"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message } from "@/lib/types";
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

  const handleReady = useCallback((submit: (text: string) => void) => {
    submitRef.current = submit;
  }, []);

  const handleExampleClick = useCallback((query: string) => {
    submitRef.current?.(query);
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setThreadId(uuidv4());
  }, []);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(
    () => setSidebarOpen((prev) => !prev),
    [],
  );

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

        {/* Mobile sidebar drawer — slide-over with backdrop */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/40"
              onClick={closeSidebar}
              aria-hidden="true"
            />
            {/* Drawer */}
            <div className="relative z-10 h-full w-[280px] animate-slide-in-left shadow-xl">
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
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            setMessages={setMessages}
            threadId={threadId}
            setThreadId={setThreadId}
            onReady={handleReady}
          />

          {/* Clinical disclaimer */}
          <ClinicalDisclaimer />
        </div>
      </div>
    </div>
  );
}
