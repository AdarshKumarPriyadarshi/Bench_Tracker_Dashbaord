"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
    staleTime: 300_000,
  });
}
