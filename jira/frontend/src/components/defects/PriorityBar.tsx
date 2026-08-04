"use client";

interface PriorityItem {
  priority: string;
  count: number;
  color: string;
}

interface PriorityBarProps {
  priorities: PriorityItem[];
  total: number;
}

export function PriorityBar({ priorities, total }: PriorityBarProps) {
  if (!priorities.length || total === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <h4 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">Priority Distribution</h4>
      <div className="flex items-center gap-3 mb-2 flex-wrap">
        {priorities.map((p) => (
          <span key={p.priority} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} />
            {p.priority}: <strong>{p.count}</strong>
          </span>
        ))}
      </div>
      <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden flex">
        {priorities.map((p) => (
          <div
            key={p.priority}
            className="h-full transition-all"
            style={{ width: `${(p.count / total) * 100}%`, backgroundColor: p.color }}
            title={`${p.priority}: ${p.count}`}
          />
        ))}
      </div>
    </div>
  );
}
