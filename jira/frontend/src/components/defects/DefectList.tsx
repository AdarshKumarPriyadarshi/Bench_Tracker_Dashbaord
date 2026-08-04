"use client";

import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Badge } from "@/components/shared/Badge";
import type { Issue } from "@/lib/types";

interface DefectListProps {
  issues: Issue[];
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
  selectedSysFunc: string | null;
}

const JIRA_BASE_URL = "https://mercedes-benz.atlassian.net/browse/";

export function DefectList({ issues, page, totalPages, total, onPageChange, selectedSysFunc }: DefectListProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
        <h4 className="text-sm font-bold text-gray-700 dark:text-gray-200">
          Defect List {selectedSysFunc && <span className="text-blue-600 ml-1">[{selectedSysFunc}]</span>}
        </h4>
        <span className="text-xs text-gray-400">{total} defects</span>
      </div>

      {issues.length === 0 ? (
        <div className="p-8 text-center text-sm text-gray-400">No defects found.</div>
      ) : (
        <div>
          <table className="w-full text-left text-sm table-fixed">
            <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
              <tr className="text-xs text-gray-500 dark:text-gray-400 font-semibold">
                <th className="p-3 w-[12%]">Key</th>
                <th className="p-3 w-[8%]">Status</th>
                <th className="p-3 w-[7%]">Priority</th>
                <th className="p-3 w-[25%]">Summary</th>
                <th className="p-3 w-[10%]">Reporter</th>
                <th className="p-3 w-[10%]">Assignee</th>
                <th className="p-3 w-[28%]">Latest Comment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {issues.map((issue) => (
                <tr key={issue.key} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <td className="p-3 font-semibold whitespace-nowrap">
                    <a
                      href={`${JIRA_BASE_URL}${issue.key}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline inline-flex items-center gap-0.5"
                    >
                      {issue.key}
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </td>
                  <td className="p-3">
                    <StatusBadge status={issue.status.name} />
                  </td>
                  <td className="p-3">
                    <PriorityDot priority={issue.priority} />
                  </td>
                  <td className="p-3 text-gray-700 dark:text-gray-300 truncate" title={issue.summary}>
                    {issue.summary}
                  </td>
                  <td className="p-3 text-gray-600 dark:text-gray-400 text-xs">
                    {issue.reporter?.display_name || "Unknown"}
                  </td>
                  <td className="p-3 text-gray-600 dark:text-gray-400 text-xs">
                    {issue.assignee?.display_name || "Unassigned"}
                  </td>
                  <td className="p-3 text-gray-500 dark:text-gray-400 text-xs truncate" title={issue.latest_comment?.body || ""}>
                    {issue.latest_comment ? issue.latest_comment.body : <span className="text-gray-300">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between p-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="flex items-center gap-1 px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          <ChevronLeft className="h-3 w-3" /> Prev
        </button>
        <span>Page {page} of {totalPages}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="flex items-center gap-1 px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Next <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    "Open": "bg-yellow-100 text-yellow-800 border-yellow-200",
    "To Do": "bg-orange-100 text-orange-800 border-orange-200",
    "In Progress": "bg-blue-100 text-blue-800 border-blue-200",
    "Testing": "bg-cyan-100 text-cyan-800 border-cyan-200",
    "Done": "bg-green-100 text-green-800 border-green-200",
    "Rejected": "bg-red-100 text-red-800 border-red-200",
    "Closed": "bg-gray-100 text-gray-800 border-gray-200",
  };
  const cls = styles[status] || "bg-gray-100 text-gray-700 border-gray-200";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border ${cls}`}>
      {status}
    </span>
  );
}

function PriorityDot({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Highest: "bg-red-500", High: "bg-orange-400", Medium: "bg-yellow-400", Low: "bg-blue-400", Lowest: "bg-gray-300",
  };
  return (
    <span className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
      <span className={`h-2 w-2 rounded-full ${colors[priority] || "bg-gray-300"}`} />
      {priority}
    </span>
  );
}
