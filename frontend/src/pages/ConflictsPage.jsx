import React, { useEffect, useState } from "react";
import api from "../services/api";
import {
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";

const SEVERITY_STYLES = {
  CRITICAL: "bg-rose-100 text-rose-800 border-rose-300",
  HIGH: "bg-rose-50 text-rose-700 border-rose-200",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
  LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState([]);
  const [filterType, setFilterType] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [loading, setLoading] = useState(false);

  function loadConflicts() {
    setLoading(true);
    const params = {};
    if (filterType) params.conflict_type = filterType;
    if (filterSeverity) params.severity = filterSeverity;
    api
      .get("/conflicts/", { params })
      .then((res) => setConflicts(res.data.results || res.data))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadConflicts();
  }, [filterType, filterSeverity]);

  const byType = conflicts.reduce((acc, c) => {
    acc[c.conflict_type] = (acc[c.conflict_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Geospatial Conflict Registry</h1>
          <p className="text-xs text-slate-500 mt-1">
            Auditable log of boundary disputes, overlapping claims, slivers, and attribute discrepancies.
          </p>
        </div>

        <button
          onClick={loadConflicts}
          disabled={loading}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors self-start sm:self-auto"
          title="Refresh conflicts"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(byType).map(([type, count]) => (
          <div key={type} className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              {type.replace(/_/g, " ")}
            </div>
            <div className="text-xl font-bold text-slate-900 mt-1">{count}</div>
          </div>
        ))}
        {Object.keys(byType).length === 0 && (
          <div className="col-span-5 bg-white border border-slate-200 rounded-xl p-4 text-center text-xs text-slate-400">
            No active conflicts detected in current datasets.
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-wrap items-center gap-3">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          className="border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-700 bg-slate-50 focus:outline-none"
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
        >
          <option value="">All Severities</option>
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          className="border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-700 bg-slate-50 focus:outline-none"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All Conflict Types</option>
          {[
            "BOUNDARY_DISCREPANCY",
            "AREA_MISMATCH",
            "ATTRIBUTE_MISMATCH",
            "BUILDING_CROSSES_PARCEL",
            "UTILITY_CROSSES_PARCEL",
            "DUPLICATE_PARCEL",
            "MISSING_PARCEL",
          ].map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        <span className="text-xs text-slate-400 ml-auto font-mono">
          Showing {conflicts.length} conflict{conflicts.length === 1 ? "" : "s"}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3">Conflict ID</th>
                <th className="px-4 py-3">Conflict Type</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Description & Rationale</th>
                <th className="px-4 py-3">Detection Confidence</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {conflicts.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-5 py-3 font-mono font-bold text-slate-900">#{c.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {c.conflict_type.replace(/_/g, " ")}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        SEVERITY_STYLES[c.severity] || "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {c.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-md truncate" title={c.description}>
                    {c.description}
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-800">
                    {c.confidence !== undefined ? `${c.confidence.toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}

              {conflicts.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-slate-400">
                    <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400 mb-2" />
                    <div className="font-semibold text-slate-700 text-sm">No conflicts found</div>
                    <div className="text-xs text-slate-400 mt-1">
                      All ingested parcels adhere to topological and attribute thresholds.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
