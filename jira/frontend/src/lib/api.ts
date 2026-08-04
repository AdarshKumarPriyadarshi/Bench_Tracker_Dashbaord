import type {
  IssueListResponse,
  ProjectListResponse,
  BoardListResponse,
  BoardIssuesResponse,
  SprintListResponse,
  AnalyticsOverview,
  BurndownResponse,
  VelocityResponse,
  TrendResponse,
  FilterParams,
  Issue,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }));
    throw new Error(error.error?.message || `API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  getProjects: () => fetchApi<ProjectListResponse>("/api/projects"),

  getProjectIssues: (projectKey: string, filters: FilterParams = {}) => {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.page_size) params.set("page_size", String(filters.page_size));
    if (filters.search) params.set("search", filters.search);
    if (filters.assignee) params.set("assignee", filters.assignee);
    if (filters.status) params.set("status", filters.status);
    if (filters.label) params.set("label", filters.label);
    const query = params.toString();
    return fetchApi<IssueListResponse>(`/api/projects/${projectKey}/issues${query ? `?${query}` : ""}`);
  },

  getIssue: (issueKey: string) => fetchApi<Issue>(`/api/issues/${issueKey}`),

  getBoards: (projectKey?: string) => {
    const params = projectKey ? `?project_key=${projectKey}` : "";
    return fetchApi<BoardListResponse>(`/api/boards${params}`);
  },

  getBoardIssues: (boardId: number) =>
    fetchApi<BoardIssuesResponse>(`/api/boards/${boardId}/issues`),

  getBoardIssuesList: (boardId: number, page = 1, pageSize = 50) =>
    fetchApi<IssueListResponse>(`/api/boards/${boardId}/issues/list?page=${page}&page_size=${pageSize}`),

  getBoardSprints: (boardId: number) =>
    fetchApi<SprintListResponse>(`/api/boards/${boardId}/sprints`),

  getSprintIssues: (sprintId: number, page = 1, pageSize = 50) =>
    fetchApi<IssueListResponse>(`/api/sprints/${sprintId}/issues?page=${page}&page_size=${pageSize}`),

  getAnalyticsOverview: (projectKey: string) =>
    fetchApi<AnalyticsOverview>(`/api/analytics/overview/${projectKey}`),

  getBurndown: (boardId: number, sprintId: number) =>
    fetchApi<BurndownResponse>(`/api/analytics/burndown?board_id=${boardId}&sprint_id=${sprintId}`),

  getVelocity: (boardId: number, sprintCount = 8) =>
    fetchApi<VelocityResponse>(`/api/analytics/velocity?board_id=${boardId}&sprint_count=${sprintCount}`),

  getTrends: (projectKey: string, days = 30) =>
    fetchApi<TrendResponse>(`/api/analytics/trends?project_key=${projectKey}&days=${days}`),

  // Defect endpoints
  getDefectOverview: (projectKey: string, release?: string, releaseCandidate?: string, safetyType?: string) => {
    const params = new URLSearchParams({ project_key: projectKey });
    if (release) params.set("release", release);
    if (releaseCandidate) params.set("release_candidate", releaseCandidate);
    if (safetyType) params.set("safety_type", safetyType);
    return fetchApi<any>(`/api/defects/overview?${params}`);
  },

  getDefectBySysFunc: (projectKey: string, release?: string, releaseCandidate?: string, safetyType?: string) => {
    const params = new URLSearchParams({ project_key: projectKey });
    if (release) params.set("release", release);
    if (releaseCandidate) params.set("release_candidate", releaseCandidate);
    if (safetyType) params.set("safety_type", safetyType);
    return fetchApi<any>(`/api/defects/by-sysfunc?${params}`);
  },

  getDefectList: (projectKey: string, filters: { release?: string; releaseCandidate?: string; safetyType?: string; sysfunc?: string; status?: string; page?: number }) => {
    const params = new URLSearchParams({ project_key: projectKey });
    if (filters.release) params.set("release", filters.release);
    if (filters.releaseCandidate) params.set("release_candidate", filters.releaseCandidate);
    if (filters.safetyType) params.set("safety_type", filters.safetyType);
    if (filters.sysfunc) params.set("sysfunc", filters.sysfunc);
    if (filters.status) params.set("status", filters.status);
    if (filters.page) params.set("page", String(filters.page));
    return fetchApi<any>(`/api/defects/list?${params}`);
  },

  getDefectTrend: (projectKey: string, days = 7, release?: string, releaseCandidate?: string, safetyType?: string) => {
    const params = new URLSearchParams({ project_key: projectKey, days: String(days) });
    if (release) params.set("release", release);
    if (releaseCandidate) params.set("release_candidate", releaseCandidate);
    if (safetyType) params.set("safety_type", safetyType);
    return fetchApi<any>(`/api/defects/trend?${params}`);
  },
};
