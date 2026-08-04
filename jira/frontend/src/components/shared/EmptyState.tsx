import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  message?: string;
}

export function EmptyState({ title = "No data", message = "No items found." }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <Inbox className="h-12 w-12 mb-3" />
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="text-xs mt-1">{message}</p>
    </div>
  );
}
