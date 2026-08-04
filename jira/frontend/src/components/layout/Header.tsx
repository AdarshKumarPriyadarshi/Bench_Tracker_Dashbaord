"use client";

import { useState, useEffect } from "react";
import { useProjectStore } from "@/store/projectStore";
import { useFilterStore } from "@/store/filterStore";
import { Search, Command } from "lucide-react";
import { useRouter } from "next/navigation";

export function Header() {
  const { activeProject } = useProjectStore();
  const { setSearch } = useFilterStore();
  const [showSearch, setShowSearch] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowSearch(true);
      }
      if (e.key === "Escape") {
        setShowSearch(false);
      }
      if (e.key === "/" && !showSearch && document.activeElement?.tagName !== "INPUT") {
        e.preventDefault();
        setShowSearch(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchValue);
    setShowSearch(false);
    router.push("/dashboard");
  };

  return (
    <>
      <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-center px-6 sticky top-0 z-20 relative">
        <h1 className="text-xl font-extrabold text-gray-900 dark:text-white tracking-tight">SysFunc Defect Tracking Dashboard</h1>

        <div className="absolute right-6 flex items-center gap-3">
          <span className="px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 text-xs font-medium rounded-full">
            {activeProject || "ADASDAI"}
          </span>

          <button
            onClick={() => setShowSearch(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search...</span>
            <kbd className="hidden sm:flex items-center gap-0.5 text-[10px] font-medium bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
              <Command className="h-2.5 w-2.5" />K
            </kbd>
          </button>

          <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">AP</span>
          </div>
        </div>
      </header>

      {showSearch && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowSearch(false)} />
          <div className="relative w-full max-w-lg bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
            <form onSubmit={handleSearch}>
              <div className="flex items-center px-4 border-b border-gray-100 dark:border-gray-700">
                <Search className="h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  autoFocus
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  placeholder="Search issues by summary..."
                  className="flex-1 px-3 py-4 text-sm bg-transparent border-0 focus:ring-0 focus:outline-none text-gray-900 dark:text-white placeholder-gray-400"
                />
                <kbd className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                  Esc
                </kbd>
              </div>
            </form>
            <div className="p-3 text-xs text-gray-400">
              Press Enter to search in the dashboard. Press Esc to close.
            </div>
          </div>
        </div>
      )}
    </>
  );
}
