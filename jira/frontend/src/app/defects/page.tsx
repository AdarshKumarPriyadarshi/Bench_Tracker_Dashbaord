"use client";

import { useState, useMemo } from "react";
import { useDefectOverview, useDefectBySysFunc, useDefectList } from "@/hooks/useDefects";
import { CATEGORIES, SYSFUNC_LIST } from "@/lib/sysfunc-data";
import { DefectStatsCards } from "@/components/defects/DefectStatsCards";
import { DefectDonut } from "@/components/defects/DefectDonut";
import { ModuleBarChart } from "@/components/defects/WeeklyTrend";
import { CategoryTabs } from "@/components/defects/CategoryTabs";
import { SysFuncTable } from "@/components/defects/SysFuncTable";
import { DefectList } from "@/components/defects/DefectList";
import { Spinner } from "@/components/shared/Spinner";

const PROJECT_KEY = "ADASDAI";
const RELEASE_VERSIONS = ["All Releases", "R16", "R17", "R18", "R19", "R21"];
const RELEASE_CANDIDATES = ["All Candidates", "MF4", "MF5"];
const SAFETY_TYPES = ["All Safety", "FUSA", "NON_FUSA"];

export default function DefectsPage() {
  const [releaseVersion, setReleaseVersion] = useState("All Releases");
  const [releaseCandidate, setReleaseCandidate] = useState("All Candidates");
  const [safetyType, setSafetyType] = useState("All Safety");
  const [activeCategory, setActiveCategory] = useState(CATEGORIES[0]);
  const [selectedSysFunc, setSelectedSysFunc] = useState<string | null>(null);
  const [defectPage, setDefectPage] = useState(1);


  const releaseFilter = releaseVersion === "All Releases" ? undefined : releaseVersion;
  const rcFilter = releaseCandidate === "All Candidates" ? undefined : releaseCandidate;
  const safetyFilter = safetyType === "All Safety" ? undefined : safetyType;

  const { data: overview, isLoading: overviewLoading } = useDefectOverview(PROJECT_KEY, releaseFilter, rcFilter, safetyFilter);
  const { data: sysfuncData, isLoading: sysfuncLoading } = useDefectBySysFunc(PROJECT_KEY, releaseFilter, rcFilter, safetyFilter);

  const categorySysFuncs = useMemo(() => {
    return SYSFUNC_LIST.filter((sf) => sf.category === activeCategory).map((sf) => sf.acronym).join(",");
  }, [activeCategory]);

  const { data: defectListData, isLoading: listLoading } = useDefectList(PROJECT_KEY, {
    release: releaseFilter,
    releaseCandidate: rcFilter,
    safetyType: safetyFilter,
    sysfunc: selectedSysFunc || categorySysFuncs,
    status: "open",
    page: defectPage,
  });

  const categoryWithCounts = useMemo(() => {
    if (!sysfuncData) return CATEGORIES.map((c) => ({ name: c, count: 0 }));
    return CATEGORIES.map((cat) => ({
      name: cat,
      count: sysfuncData.sysfuncs
        .filter((sf: any) => sf.category === cat)
        .reduce((sum: number, sf: any) => sum + sf.open_count, 0),
    }));
  }, [sysfuncData]);

  const filteredSysFuncs = useMemo(() => {
    if (!sysfuncData) return [];
    return sysfuncData.sysfuncs.filter((sf: any) => sf.category === activeCategory);
  }, [sysfuncData, activeCategory]);


  const handleSysFuncSelect = (acronym: string) => {
    setSelectedSysFunc(selectedSysFunc === acronym ? null : acronym);
    setDefectPage(1);
  };

  if (overviewLoading && sysfuncLoading) return <Spinner className="h-64" />;

  return (
    <div className="space-y-5">
      {/* Filter Dropdowns */}
      <div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-4 mt-4">
          <div>
            <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Release Version</label>
            <select
              value={releaseVersion}
              onChange={(e) => setReleaseVersion(e.target.value)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[150px]"
            >
              {RELEASE_VERSIONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Release Candidate</label>
            <select
              value={releaseCandidate}
              onChange={(e) => setReleaseCandidate(e.target.value)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[150px]"
            >
              {RELEASE_CANDIDATES.map((rc) => (
                <option key={rc} value={rc}>{rc}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Safety Type</label>
            <select
              value={safetyType}
              onChange={(e) => setSafetyType(e.target.value)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[150px]"
            >
              {SAFETY_TYPES.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {overview && (
        <DefectStatsCards
          total={overview.total}
          ongoing={overview.total - overview.closed_count}
          closed={overview.closed_count}
        />
      )}

      {/* Charts Row: Donut + Weekly Trend */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {overview && <DefectDonut statusDistribution={overview.status_distribution} />}
        {sysfuncData && <ModuleBarChart data={sysfuncData.sysfuncs} />}
      </div>

      {/* Priority Bar */}

      {/* Category Tabs + SysFunc Table */}
      <CategoryTabs categories={categoryWithCounts} active={activeCategory} onSelect={(cat) => { setActiveCategory(cat); setSelectedSysFunc(null); setDefectPage(1); }} />

      {sysfuncLoading ? (
        <Spinner className="h-32" />
      ) : (
        <SysFuncTable data={filteredSysFuncs} onSelect={handleSysFuncSelect} selected={selectedSysFunc} />
      )}

      {/* Defect List */}
      {listLoading ? (
        <Spinner className="h-32" />
      ) : defectListData ? (
        <DefectList
          issues={defectListData.issues}
          page={defectListData.page}
          totalPages={defectListData.total_pages}
          total={defectListData.total}
          onPageChange={setDefectPage}
          selectedSysFunc={selectedSysFunc}
        />
      ) : null}

      {/* Aging Cards */}
    </div>
  );
}
