"use client";

import { useWebSocket } from "@/hooks/useWebSocket";

export function WebSocketProvider() {
  const { connected } = useWebSocket();

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-white dark:bg-gray-800 rounded-full shadow-sm border border-gray-200 dark:border-gray-700 text-xs">
        <div className={`h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-300"}`} />
        <span className="text-gray-500 dark:text-gray-400">
          {connected ? "Live" : "Offline"}
        </span>
      </div>
    </div>
  );
}
