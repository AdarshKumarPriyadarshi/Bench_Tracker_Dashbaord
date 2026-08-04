"use client";

interface AgingBucket {
  label: string;
  count: number;
  color: string;
}

interface AgingCardsProps {
  buckets: AgingBucket[];
}

const BG_MAP: Record<string, string> = {
  "#22c55e": "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
  "#eab308": "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800",
  "#f97316": "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
  "#dc2626": "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
};

const TEXT_MAP: Record<string, string> = {
  "#22c55e": "text-green-700 dark:text-green-300",
  "#eab308": "text-yellow-700 dark:text-yellow-300",
  "#f97316": "text-orange-700 dark:text-orange-300",
  "#dc2626": "text-red-700 dark:text-red-300",
};

export function AgingCards({ buckets }: AgingCardsProps) {
  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <h4 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">Defect Aging</h4>
      <div className="grid grid-cols-4 gap-3">
        {buckets.map((b) => (
          <div
            key={b.label}
            className={`p-3 rounded-lg border text-center ${BG_MAP[b.color] || ""}`}
          >
            <p className={`text-2xl font-bold ${TEXT_MAP[b.color] || "text-gray-900"}`}>{b.count}</p>
            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">{b.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
