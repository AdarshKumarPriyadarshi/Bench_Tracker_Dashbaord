"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings, Moon, Sun, Bug } from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/defects", label: "Defect Dashboard", icon: Bug },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [darkMode, setDarkMode] = useState(false);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle("dark");
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col z-30">
      <div className="h-16 flex items-center px-5 border-b border-gray-100 dark:border-gray-800">
        <h1 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Jira Dashboard</h1>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-100 dark:border-gray-800 space-y-3">
        <button
          onClick={toggleDarkMode}
          className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          {darkMode ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          {darkMode ? "Light Mode" : "Dark Mode"}
        </button>
        <p className="text-xs text-gray-400 dark:text-gray-500 px-3">ADAS Platform v2.0</p>
      </div>
    </aside>
  );
}
