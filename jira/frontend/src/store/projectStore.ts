import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ProjectState {
  activeProject: string | null;
  activeBoard: number | null;
  activeSprint: number | null;
  setProject: (key: string) => void;
  setBoard: (id: number | null) => void;
  setSprint: (id: number | null) => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      activeProject: "ADASDAI",
      activeBoard: null,
      activeSprint: null,
      setProject: (key) => set({ activeProject: key, activeBoard: null, activeSprint: null }),
      setBoard: (id) => set({ activeBoard: id, activeSprint: null }),
      setSprint: (id) => set({ activeSprint: id }),
    }),
    { name: "jira-project-store" }
  )
);
