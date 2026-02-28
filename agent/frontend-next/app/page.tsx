"use client";

import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message } from "@/lib/types";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState(() => uuidv4());

  const submitRef = useRef<(text: string) => void>();

  const handleReady = useCallback((submit: (text: string) => void) => {
    submitRef.current = submit;
  }, []);

  const handleExampleClick = useCallback((query: string) => {
    submitRef.current?.(query);
  }, []);

  return (
    <main className="flex h-screen">
      <Sidebar
        threadId={threadId}
        messageCount={messages.length}
        onExampleClick={handleExampleClick}
      />
      <div className="flex flex-1 flex-col">
        <ChatWindow
          messages={messages}
          setMessages={setMessages}
          threadId={threadId}
          setThreadId={setThreadId}
          onReady={handleReady}
        />
      </div>
    </main>
  );
}
