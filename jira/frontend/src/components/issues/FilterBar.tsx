"use client";

import { Search, X } from "lucide-react";
import { useFilterStore } from "@/store/filterStore";

interface FilterBarProps {
  assignees?: string[];
  statuses?: string[];
  labels?: string[];
}

export function FilterBar({ assignees = [], statuses = [], labels = [] }: FilterBarProps) {
  const { search, assignee, status, label, setSearch, setAssignee, setStatus, setLabel, resetFilters } =
    useFilterStore();

  const hasActiveFilters = search || assignee || status || label;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search issues..."
          className="w-full text-sm border border-gray-300 rounded-lg pl-9 pr-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      <select
        value={assignee}
        onChange={(e) => setAssignee(e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
      >
        <option value="">All Assignees</option>
        {assignees.map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>

      <select
        value={status}
        onChange={(e) => setStatus(e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
      >
        <option value="">All Statuses</option>
        {statuses.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
      >
        <option value="">All Labels</option>
        {labels.map((l) => (
          <option key={l} value={l}>{l}</option>
        ))}
      </select>

      {hasActiveFilters && (
        <button
          onClick={resetFilters}
          className="flex items-center justify-center gap-1 text-sm text-red-600 hover:text-red-700 font-medium"
        >
          <X className="h-3 w-3" />
          Clear
        </button>
      )}
    </div>
  );
}
