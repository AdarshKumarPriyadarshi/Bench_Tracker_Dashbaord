"use client";

import { Bug, CircleDot, CheckCircle2 } from "lucide-react";

interface DefectStatsCardsProps {
  total: number;
  ongoing: number;
  closed: number;
}

export function DefectStatsCards({ total, ongoing, closed }: DefectStatsCardsProps) {
  const cards = [
    { label: "Total Bugs", value: String(total), icon: Bug, color: "text-gray-900", border: "" },
    { label: "Ongoing", value: String(ongoing), icon: CircleDot, color: "text-blue-600", border: "border-l-4 border-l-blue-400" },
    { label: "Closed", value: String(closed), icon: CheckCircle2, color: "text-green-600", border: "border-l-4 border-l-green-500" },
  ];

  return (
    <div className="grid grid-cols-3 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className={`bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 ${card.border} transition-all hover:shadow-md`}
          >
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{card.label}</p>
              <Icon className="h-4 w-4 text-gray-300" />
            </div>
            <h3 className={`text-3xl font-bold mt-2 ${card.color}`}>{card.value}</h3>
          </div>
        );
      })}
    </div>
  );
}
