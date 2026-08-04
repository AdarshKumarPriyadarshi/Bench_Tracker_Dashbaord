"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FilterParams } from "@/lib/types";

export function useProjectIssues(projectKey: string | null, filters: FilterParams = {}) {
  return useQuery({
    queryKey: ["issues", projectKey, filters],
    queryFn: () => api.getProjectIssues(projectKey!, filters),
    enabled: !!projectKey,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useBoardIssuesList(boardId: number | null, page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ["board-issues-list", boardId, page, pageSize],
    queryFn: () => api.getBoardIssuesList(boardId!, page, pageSize),
    enabled: !!boardId,
    staleTime: 30_000,
  });
}

export function useIssueDetail(issueKey: string | null) {
  return useQuery({
    queryKey: ["issue", issueKey],
    queryFn: () => api.getIssue(issueKey!),
    enabled: !!issueKey,
  });
}
