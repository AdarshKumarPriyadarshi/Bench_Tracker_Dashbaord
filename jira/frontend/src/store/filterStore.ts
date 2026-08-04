import { create } from "zustand";

interface FilterState {
  search: string;
  assignee: string;
  status: string;
  label: string;
  page: number;
  setSearch: (value: string) => void;
  setAssignee: (value: string) => void;
  setStatus: (value: string) => void;
  setLabel: (value: string) => void;
  setPage: (value: number) => void;
  resetFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  search: "",
  assignee: "",
  status: "",
  label: "",
  page: 1,
  setSearch: (value) => set({ search: value, page: 1 }),
  setAssignee: (value) => set({ assignee: value, page: 1 }),
  setStatus: (value) => set({ status: value, page: 1 }),
  setLabel: (value) => set({ label: value, page: 1 }),
  setPage: (value) => set({ page: value }),
  resetFilters: () => set({ search: "", assignee: "", status: "", label: "", page: 1 }),
}));
