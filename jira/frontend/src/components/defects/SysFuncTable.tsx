"use client";

interface SysFuncRow {
  acronym: string;
  name: string;
  open_count: number;
  closed_count: number;
  critical_count: number;
  total: number;
}

interface SysFuncTableProps {
  data: SysFuncRow[];
  onSelect: (acronym: string) => void;
  selected: string | null;
}

export function SysFuncTable({ data, onSelect, selected }: SysFuncTableProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
      <table className="w-full text-left text-sm">
        <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <tr className="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase tracking-wider">
            <th className="p-3">Acronym</th>
            <th className="p-3">System Function</th>
            <th className="p-3 text-center">Ongoing</th>
            <th className="p-3 text-center">Closed</th>
            <th className="p-3 text-center">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {data.map((row) => (
            <tr
              key={row.acronym}
              onClick={() => onSelect(row.acronym)}
              className={`cursor-pointer transition-colors ${
                selected === row.acronym
                  ? "bg-blue-50 dark:bg-blue-900/20"
                  : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
              }`}
            >
              <td className="p-3 font-bold text-blue-600 dark:text-blue-400">{row.acronym}</td>
              <td className="p-3 text-gray-700 dark:text-gray-300 truncate max-w-[250px]">{row.name}</td>
              <td className="p-3 text-center">
                {row.open_count > 0 ? (
                  <span className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 text-xs font-bold bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">{row.open_count}</span>
                ) : (
                  <span className="text-gray-300">0</span>
                )}
              </td>
              <td className="p-3 text-center">
                {row.closed_count > 0 ? (
                  <span className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 text-xs font-bold bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">{row.closed_count}</span>
                ) : (
                  <span className="text-gray-300">0</span>
                )}
              </td>
              <td className="p-3 text-center font-semibold text-gray-900 dark:text-white">{row.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
