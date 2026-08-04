"use client";

import { useProjectStore } from "@/store/projectStore";
import { useFilterStore } from "@/store/filterStore";
import { RefreshCw, Trash2 } from "lucide-react";

export default function SettingsPage() {
  const { activeProject, activeBoard, setProject } = useProjectStore();
  const { resetFilters } = useFilterStore();

  const handleClearCache = () => {
    localStorage.clear();
    window.location.reload();
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Settings</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Dashboard configuration and preferences</p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 space-y-4">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200">Connection</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
            <span className="text-gray-500 dark:text-gray-400">API Backend</span>
            <span className="font-medium text-gray-900 dark:text-white">http://localhost:8000</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
            <span className="text-gray-500 dark:text-gray-400">Active Project</span>
            <span className="font-medium text-gray-900 dark:text-white">{activeProject || "None"}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
            <span className="text-gray-500 dark:text-gray-400">Active Board</span>
            <span className="font-medium text-gray-900 dark:text-white">{activeBoard || "None"}</span>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 space-y-4">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200">Keyboard Shortcuts</h3>
        <div className="space-y-2 text-sm">
          <ShortcutRow keys={["Ctrl", "K"]} description="Open global search" />
          <ShortcutRow keys={["/"]} description="Focus search (when not in input)" />
          <ShortcutRow keys={["Esc"]} description="Close modals" />
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 space-y-4">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200">Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={resetFilters}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Reset Filters
          </button>
          <button
            onClick={handleClearCache}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            Clear Cache & Reload
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">About</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Jira Dashboard v2.0 — ADAS Platform Team Tool
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
          Backend: FastAPI + httpx | Frontend: Next.js 16 + Tailwind CSS + Recharts
        </p>
      </div>
    </div>
  );
}

function ShortcutRow({ keys, description }: { keys: string[]; description: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-gray-500 dark:text-gray-400">{description}</span>
      <div className="flex gap-1">
        {keys.map((k) => (
          <kbd key={k} className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded border border-gray-200 dark:border-gray-600">
            {k}
          </kbd>
        ))}
      </div>
    </div>
  );
}
