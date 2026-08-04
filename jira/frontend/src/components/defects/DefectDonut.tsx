"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface StatusItem {
  status: string;
  count: number;
  color: string;
}

interface DefectDonutProps {
  statusDistribution: StatusItem[];
}

const STATUS_COLORS: Record<string, string> = {
  "Open": "#eab308",
  "Refinement": "#8b5cf6",
  "To Do": "#f97316",
  "In Progress": "#3b82f6",
  "Blocked (Migrated)": "#f97316",
  "Testing": "#06b6d4",
  "Done": "#22c55e",
  "Under Observation": "#8b5cf6",
  "Reopened": "#ec4899",
  "Rejected": "#dc2626",
};

export function DefectDonut({ statusDistribution }: DefectDonutProps) {
  const ongoingStatuses = (statusDistribution || []).filter(
    (s) => s.status.toLowerCase() !== "closed"
  );

  const hasData = ongoingStatuses.length > 0 && ongoingStatuses.some((s) => s.count > 0);

  const data = hasData
    ? ongoingStatuses.map((s) => ({
        name: s.status,
        value: s.count,
        color: STATUS_COLORS[s.status] || s.color || "#94a3b8",
      }))
    : [{ name: "No Data", value: 1, color: "#e5e7eb" }];

  const total = hasData ? data.reduce((sum, d) => sum + d.value, 0) : 0;

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <h4 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-2">Ongoing Status</h4>
      <div className="relative h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={85}
              dataKey="value"
              nameKey="name"
              strokeWidth={2}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            {hasData && <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />}
            {hasData && (
              <Legend
                wrapperStyle={{ fontSize: 11 }}
                formatter={(value: string) => <span className="text-gray-600 dark:text-gray-300">{value}</span>}
              />
            )}
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <span className="text-2xl font-bold text-gray-900 dark:text-white">{total}</span>
          <span className="text-[10px] text-gray-400 uppercase">{hasData ? "Ongoing" : "No Data"}</span>
        </div>
      </div>
    </div>
  );
}
