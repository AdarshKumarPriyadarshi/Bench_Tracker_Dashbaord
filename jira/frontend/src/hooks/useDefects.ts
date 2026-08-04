"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDefectOverview(projectKey: string, release?: string, releaseCandidate?: string, safetyType?: string) {
  return useQuery({
    queryKey: ["defect-overview", projectKey, release, releaseCandidate, safetyType],
    queryFn: () => api.getDefectOverview(projectKey, release, releaseCandidate, safetyType),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

export function useDefectBySysFunc(projectKey: string, release?: string, releaseCandidate?: string, safetyType?: string) {
  return useQuery({
    queryKey: ["defect-by-sysfunc", projectKey, release, releaseCandidate, safetyType],
    queryFn: () => api.getDefectBySysFunc(projectKey, release, releaseCandidate, safetyType),
    staleTime: 60_000,
  });
}

export function useDefectList(projectKey: string, params: { release?: string; releaseCandidate?: string; safetyType?: string; sysfunc?: string; status?: string; page?: number }) {
  return useQuery({
    queryKey: ["defect-list", projectKey, params],
    queryFn: () => api.getDefectList(projectKey, params),
    staleTime: 30_000,
  });
}

export function useDefectTrend(projectKey: string, days = 7, release?: string, releaseCandidate?: string, safetyType?: string) {
  return useQuery({
    queryKey: ["defect-trend", projectKey, days, release, releaseCandidate, safetyType],
    queryFn: () => api.getDefectTrend(projectKey, days, release, releaseCandidate, safetyType),
    staleTime: 120_000,
  });
}
