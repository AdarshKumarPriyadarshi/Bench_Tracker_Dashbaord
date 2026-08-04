"use client";

interface CategoryTabsProps {
  categories: { name: string; count: number }[];
  active: string;
  onSelect: (category: string) => void;
}

export function CategoryTabs({ categories, active, onSelect }: CategoryTabsProps) {
  return (
    <div className="flex flex-wrap gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
      {categories.map((cat) => (
        <button
          key={cat.name}
          onClick={() => onSelect(cat.name)}
          className={`px-3 py-2 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            active === cat.name
              ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
              : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          }`}
        >
          {cat.name} <span className="ml-1 text-gray-400">({cat.count})</span>
        </button>
      ))}
    </div>
  );
}
