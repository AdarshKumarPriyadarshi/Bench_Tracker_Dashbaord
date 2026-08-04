"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LabelList } from "recharts";

interface ModuleDefect {
  acronym: string;
  open_count: number;
}

interface ModuleBarChartProps {
  data: ModuleDefect[];
}

export function ModuleBarChart({ data }: ModuleBarChartProps) {
  const ongoingModules = (data || [])
    .filter((d) => d.open_count > 0)
    .sort((a, b) => b.open_count - a.open_count);

  const hasData = ongoingModules.length > 0;

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <h4 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-2">Module Wise Distribution</h4>
      <div className="h-56">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ongoingModules} margin={{ top: 20, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="acronym"
                tick={{ fontSize: 10, fill: "#64748b" }}
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                angle={-30}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                allowDecimals={false}
              />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="open_count" fill="#f97316" name="Ongoing" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="open_count" position="top" style={{ fontSize: 11, fill: "#374151", fontWeight: 600 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="relative h-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[]} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} domain={[0, 10]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm text-gray-400 bg-white/80 dark:bg-gray-800/80 px-3 py-1 rounded">No data available</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
