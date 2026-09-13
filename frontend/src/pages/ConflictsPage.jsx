import React, { useEffect, useState } from "react";
import api from "../services/api";

const SEVERITY_TONE = {
  CRITICAL: "status-badge-low", HIGH: "status-badge-low",
  MEDIUM: "status-badge-medium", LOW: "status-badge-high",
};

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState([]);
  const [filterType, setFilterType] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");

  useEffect(() => {
    const params = {};
    if (filterType) params.conflict_type = filterType;
    if (filterSeverity) params.severity = filterSeverity;
    api.get("/conflicts/", { params }).then((res) => setConflicts(res.data.results || res.data));
  }, [filterType, filterSeverity]);

  const byType = conflicts.reduce((acc, c) => {
    acc[c.conflict_type] = (acc[c.conflict_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Conflict Dashboard</h1>
      <p className="text-sm text-ink-500 mb-4">Boundary, attribute, topology, and unmatched-parcel issues.</p>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        {Object.entries(byType).map(([type, count]) => (
          <div key={type} className="card p-3">
            <div className="text-xs text-ink-500">{type.replace(/_/g, " ")}</div>
            <div className="text-xl font-semibold text-ink-900">{count}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mb-3">
        <select className="border border-ink-200 rounded-md px-2 py-1.5 text-sm" value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}>
          <option value="">All severities</option>
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-500 text-xs uppercase"><tr>
            <th className="text-left px-4 py-2">ID</th><th className="text-left px-4 py-2">Type</th>
            <th className="text-left px-4 py-2">Severity</th><th className="text-left px-4 py-2">Description</th>
            <th className="text-left px-4 py-2">Confidence</th><th className="text-left px-4 py-2">Status</th>
          </tr></thead>
          <tbody>
            {conflicts.map((c) => (
              <tr key={c.id} className="border-t border-ink-100">
                <td className="px-4 py-2">{c.id}</td>
                <td className="px-4 py-2">{c.conflict_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-2"><span className={`status-badge ${SEVERITY_TONE[c.severity]}`}>{c.severity}</span></td>
                <td className="px-4 py-2 text-ink-600 max-w-md truncate">{c.description}</td>
                <td className="px-4 py-2">{c.confidence?.toFixed(1)}%</td>
                <td className="px-4 py-2">{c.status}</td>
              </tr>
            ))}
            {conflicts.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-ink-400">No conflicts found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
