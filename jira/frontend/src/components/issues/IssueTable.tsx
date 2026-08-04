"use client";

import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Badge } from "@/components/shared/Badge";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Issue } from "@/lib/types";

interface IssueTableProps {
  issues: Issue[];
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}

const JIRA_BASE_URL = "https://mercedes-benz.atlassian.net/browse/";

export function IssueTable({ issues, page, totalPages, total, onPageChange }: IssueTableProps) {
  if (!issues.length) {
    return <EmptyState title="No issues found" message="Try adjusting your filters." />;
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="p-4 border-b border-gray-100">
        <h4 className="text-sm font-bold text-gray-700">Issues ({total})</h4>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr className="text-gray-500 font-semibold">
              <th className="p-3">Key</th>
              <th className="p-3">Summary</th>
              <th className="p-3">Assignee</th>
              <th className="p-3">Status</th>
              <th className="p-3">Labels</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {issues.map((issue) => (
              <tr key={issue.key} className="hover:bg-gray-50/80 transition-colors">
                <td className="p-3 font-semibold">
                  <a
                    href={`${JIRA_BASE_URL}${issue.key}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline inline-flex items-center gap-1"
                  >
                    {issue.key}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
                <td className="p-3 text-gray-600 max-w-xs truncate" title={issue.summary}>
                  {issue.summary}
                </td>
                <td className="p-3 text-gray-900 font-medium">
                  {issue.assignee?.display_name || "Unassigned"}
                </td>
                <td className="p-3">
                  <StatusBadge status={issue.status.name} category={issue.status.category} />
                </td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-1">
                    {issue.labels.map((l) => (
                      <Badge key={l}>{l}</Badge>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between p-4 border-t border-gray-100 text-sm text-gray-500">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="flex items-center gap-1 px-3 py-1.5 border rounded-md disabled:opacity-40 hover:bg-gray-50"
        >
          <ChevronLeft className="h-4 w-4" /> Previous
        </button>
        <span>Page {page} of {totalPages}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="flex items-center gap-1 px-3 py-1.5 border rounded-md disabled:opacity-40 hover:bg-gray-50"
        >
          Next <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ status, category }: { status: string; category: string }) {
  const variant = category === "done" ? "success" : category === "in_progress" ? "info" : "default";
  return <Badge variant={variant}>{status}</Badge>;
}
