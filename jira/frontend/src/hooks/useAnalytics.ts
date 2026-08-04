"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useAnalyticsOverview(projectKey: string | null) {
  return useQuery({
    queryKey: ["analytics-overview", projectKey],
    queryFn: () => api.getAnalyticsOverview(projectKey!),
    enabled: !!projectKey,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

export function useBurndown(boardId: number | null, sprintId: number | null) {
  return useQuery({
    queryKey: ["burndown", boardId, sprintId],
    queryFn: () => api.getBurndown(boardId!, sprintId!),
    enabled: !!boardId && !!sprintId,
    staleTime: 300_000,
  });
}

export function useVelocity(boardId: number | null, sprintCount = 8) {
  return useQuery({
    queryKey: ["velocity", boardId, sprintCount],
    queryFn: () => api.getVelocity(boardId!, sprintCount),
    enabled: !!boardId,
    staleTime: 300_000,
  });
}

export function useTrends(projectKey: string | null, days = 30) {
  return useQuery({
    queryKey: ["trends", projectKey, days],
    queryFn: () => api.getTrends(projectKey!, days),
    enabled: !!projectKey,
    staleTime: 300_000,
  });
}
