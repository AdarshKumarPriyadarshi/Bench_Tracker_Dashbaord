export interface SysFunc {
  id: number;
  name: string;
  acronym: string;
  category: string;
  tester: string;
  safetyRelevant: boolean;
}

export const SYSFUNC_LIST: SysFunc[] = [
  { id: 1, name: "Provide Inputs for Dimming Functions", acronym: "Dimming", category: "Miscellaneous", tester: "Suraj M", safetyRelevant: true },
  { id: 2, name: "Provide Radar Data", acronym: "PRD", category: "Miscellaneous", tester: "Vysiya S", safetyRelevant: true },
  { id: 3, name: "Determine Global Time Sync", acronym: "GTS", category: "Miscellaneous", tester: "Vysiya S", safetyRelevant: true },
  { id: 4, name: "Determine Parking Operation Mode", acronym: "POM", category: "Parking", tester: "Surya J", safetyRelevant: true },
  { id: 5, name: "Provide Image And Video Data for Park Damage Detection", acronym: "PDD", category: "Parking", tester: "Surya J & Nayaz", safetyRelevant: false },
  { id: 6, name: "Provide System state and Degradation state", acronym: "PSSDS", category: "Parking", tester: "Rahul G", safetyRelevant: true },
  { id: 7, name: "Determine Driver Lon Control state for parking function", acronym: "DLCS", category: "Parking", tester: "Surya J", safetyRelevant: true },
  { id: 8, name: "Determine driver Lon_Lat Requests for parking function", acronym: "DLLR", category: "Parking", tester: "Suraj M", safetyRelevant: true },
  { id: 9, name: "Startup/Shutdown/PNC", acronym: "SSPN", category: "Miscellaneous", tester: "Vysiya S", safetyRelevant: false },
  { id: 10, name: "SEM: ROV DTC", acronym: "SEM_ROV", category: "Miscellaneous", tester: "Rahul G & Bharath", safetyRelevant: false },
  { id: 11, name: "ODF - Provide Function Codifications System Function Content", acronym: "ODF", category: "ODF", tester: "Nayaz", safetyRelevant: true },
  { id: 12, name: "Provide Inputs for PreSafe Functions", acronym: "Presafe", category: "ROV Functions Contributions", tester: "Sushma Y S", safetyRelevant: false },
  { id: 13, name: "Coordinate in-vehicle Driver interactions and visualization for parking functions", acronym: "Visualisation", category: "Parking", tester: "Rahul G, Surya & Sushma, Kajal", safetyRelevant: false },
  { id: 14, name: "Coordinate Cleaning Heating and Precondition", acronym: "CCHP", category: "Miscellaneous", tester: "Bharath B", safetyRelevant: false },
  { id: 15, name: "Determine PTS Operation Mode", acronym: "PTS_Op_Mode", category: "Parking", tester: "Rahul G", safetyRelevant: false },
  { id: 16, name: "Determine SVS Operation Mode", acronym: "SVS_Op_Mode", category: "Parking", tester: "Surya J", safetyRelevant: false },
  { id: 17, name: "Execute Driver Warning Cascade for ALSA", acronym: "ALSA", category: "Driving Function", tester: "Kajal K", safetyRelevant: false },
  { id: 18, name: "Provide Weather Data", acronym: "PWD", category: "Miscellaneous", tester: "Bharath B", safetyRelevant: false },
  { id: 19, name: "Argumented Reality", acronym: "AR", category: "Parking", tester: "Sushma Y S & Kajal K", safetyRelevant: false },
  { id: 20, name: "Visual RIM Protection", acronym: "VRP", category: "Parking", tester: "Vysiya S", safetyRelevant: false },
  { id: 21, name: "Determine Vehicle Body parts", acronym: "VBPS", category: "Parking", tester: "Bharath B", safetyRelevant: false },
];

export const SYSFUNC_LABELS = SYSFUNC_LIST.map((sf) => sf.acronym);

export const CATEGORIES = [
  "Parking",
  "Miscellaneous",
  "Driving Function",
  "ODF",
  "ROV Functions Contributions",
];

export function getSysFuncsByCategory(category: string): SysFunc[] {
  return SYSFUNC_LIST.filter((sf) => sf.category === category);
}
