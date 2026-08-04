"use client";

import { useState } from "react";
import { useProjects } from "@/hooks/useProjects";
import { useProjectStore } from "@/store/projectStore";
import { Spinner } from "@/components/shared/Spinner";
import { SearchInput } from "@/components/shared/SearchInput";
import { FolderKanban, CheckCircle2 } from "lucide-react";

export default function ProjectsPage() {
  const { data, isLoading } = useProjects();
  const { activeProject, setProject } = useProjectStore();
  const [search, setSearch] = useState("");

  if (isLoading) return <Spinner className="h-64" />;

  const filteredProjects = data?.projects.filter((p) =>
    p.key.toLowerCase().includes(search.toLowerCase()) ||
    p.name.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Projects</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {data?.projects.length || 0} projects available
          </p>
        </div>
      </div>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search projects by key or name..."
        className="max-w-sm"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProjects.map((project) => {
          const isActive = activeProject === project.key;
          return (
            <button
              key={project.id}
              onClick={() => setProject(project.key)}
              className={`text-left p-5 rounded-xl border-2 transition-all hover:shadow-md ${
                isActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400"
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                  isActive ? "bg-blue-100 dark:bg-blue-800" : "bg-gray-100 dark:bg-gray-700"
                }`}>
                  {project.avatar_url ? (
                    <img src={project.avatar_url} alt="" className="h-8 w-8 rounded" />
                  ) : (
                    <FolderKanban className={`h-5 w-5 ${isActive ? "text-blue-600" : "text-gray-400"}`} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 dark:text-white">{project.key}</p>
                    {isActive && <CheckCircle2 className="h-4 w-4 text-blue-500" />}
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{project.name}</p>
                </div>
              </div>
              {project.project_type && (
                <span className="inline-block mt-3 text-xs font-medium text-gray-400 dark:text-gray-500 capitalize">
                  {project.project_type.replace("_", " ")}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {filteredProjects.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          No projects matching &quot;{search}&quot;
        </div>
      )}
    </div>
  );
}
