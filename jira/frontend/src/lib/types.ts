export interface StatusInfo {
  name: string;
  category: "todo" | "in_progress" | "done";
  color: string;
}

export interface UserInfo {
  account_id: string;
  display_name: string;
  email: string;
  avatar_url: string;
}

export interface SprintRef {
  id: number;
  name: string;
  state: string;
}

export interface Issue {
  key: string;
  id: string;
  summary: string;
  status: StatusInfo;
  assignee: UserInfo | null;
  reporter: UserInfo | null;
  labels: string[];
  priority: string;
  issue_type: string;
  created: string;
  updated: string;
  sprint: SprintRef | null;
  story_points: number | null;
  latest_comment: { body: string; author: string; created: string } | null;
}

export interface IssueListResponse {
  issues: Issue[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Project {
  id: string;
  key: string;
  name: string;
  avatar_url: string;
  project_type: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface Board {
  id: number;
  name: string;
  board_type: "scrum" | "kanban";
  project_key: string;
}

export interface BoardListResponse {
  boards: Board[];
}

export interface BoardIssuesResponse {
  board: Board;
  columns: Record<string, Issue[]>;
  total: number;
}

export interface Sprint {
  id: number;
  name: string;
  state: "active" | "closed" | "future";
  start_date: string | null;
  end_date: string | null;
  complete_date: string | null;
  goal: string | null;
}

export interface SprintListResponse {
  sprints: Sprint[];
}

export interface StatusDistribution {
  status: string;
  category: string;
  count: number;
  color: string;
}

export interface WorkloadEntry {
  assignee: UserInfo | null;
  assignee_name: string;
  todo: number;
  in_progress: number;
  done: number;
  total: number;
}

export interface AnalyticsOverview {
  total_issues: number;
  todo_count: number;
  in_progress_count: number;
  done_count: number;
  assignee_count: number;
  status_distribution: StatusDistribution[];
  workload: WorkloadEntry[];
}

export interface BurndownPoint {
  date: string;
  remaining: number;
  ideal: number;
}

export interface BurndownResponse {
  sprint_name: string;
  points: BurndownPoint[];
  total_scope: number;
}

export interface VelocityEntry {
  sprint_name: string;
  committed: number;
  completed: number;
}

export interface VelocityResponse {
  entries: VelocityEntry[];
}

export interface TrendPoint {
  date: string;
  created: number;
  resolved: number;
}

export interface TrendResponse {
  points: TrendPoint[];
  period_days: number;
}

export interface FilterParams {
  search?: string;
  assignee?: string;
  status?: string;
  label?: string;
  page?: number;
  page_size?: number;
}
