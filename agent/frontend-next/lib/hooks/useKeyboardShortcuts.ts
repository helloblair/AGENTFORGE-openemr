"use client";

import { useEffect } from "react";

interface UseKeyboardShortcutsOptions {
  /** Start a new conversation (Ctrl/Cmd+K). */
  onNewChat: () => void;
  /** Close the mobile sidebar drawer (Escape). */
  onCloseSidebar: () => void;
  /** Whether the sidebar drawer is currently open. */
  sidebarOpen: boolean;
}

/**
 * Global keyboard shortcuts:
 *  - Ctrl+K / Cmd+K — new conversation
 *  - Escape          — close sidebar drawer (mobile) / blur active input
 */
export function useKeyboardShortcuts({
  onNewChat,
  onCloseSidebar,
  sidebarOpen,
}: UseKeyboardShortcutsOptions) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K / Cmd+K — new chat
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onNewChat();
        return;
      }

      // Escape — close sidebar or blur active input
      if (e.key === "Escape") {
        if (sidebarOpen) {
          onCloseSidebar();
        } else if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onNewChat, onCloseSidebar, sidebarOpen]);
}
