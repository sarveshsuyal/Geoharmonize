import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";

const MATCH_ACTIONS = [
  { key: "ACCEPT", label: "Accept Match", style: "btn-primary" },
  { key: "CONFIRM_SPLIT", label: "Confirm Split (1:N)", style: "btn-secondary bg-purple-50 text-purple-700 border-purple-200" },
  { key: "CONFIRM_MERGE", label: "Confirm Merge (N:1)", style: "btn-secondary bg-indigo-50 text-indigo-700 border-indigo-200" },
  { key: "MARK_UNRESOLVED", label: "Mark Unresolved", style: "btn-secondary text-amber-700 border-amber-200" },
  { key: "REJECT", label: "Reject Match", style: "btn-secondary text-red-600 border-red-200" },
];

export default function ReviewQueuePage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run");
  const [activeTab, setActiveTab] = useState("matches"); // "matches" | "conflicts"

  // Matches state
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [matchNotes, setMatchNotes] = useState("");
  const [matchBusy, setMatchBusy] = useState(false);
  const [statusFilter, setStatusFilter] = useState("REVIEW");

  // Conflicts state
  const [conflicts, setConflicts] = useState([]);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [conflictReason, setConflictReason] = useState("");
  const [conflictBusy, setConflictBusy] = useState(false);

  function loadMatches() {
    const params = {
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(runId ? { run: runId } : {}),
    };
    api.get("/harmonization/matches/", { params }).then((res) => {
      setMatches(res.data.results || res.data);
    });
  }

  function loadConflicts() {
    api.get("/conflicts/", { params: { status: "PENDING" } }).then((res) => {
      setConflicts(res.data.results || res.data);
    });
  }

  useEffect(() => {
    loadMatches();
    loadConflicts();
  }, [statusFilter, runId]);

  async function openMatch(id) {
    const res = await api.get(`/harmonization/matches/${id}/`);
    setSelectedMatch(res.data);
    setMatchNotes("");
  }

  async function openConflict(id) {
    const res = await api.get(`/conflicts/${id}/`);
    setSelectedConflict(res.data);
    setConflictReason("");
  }

  async function resolveMatch(action, altId = null) {
    if (!selectedMatch) return;
    setMatchBusy(true);
    try {
      await api.post(`/harmonization/matches/${selectedMatch.id}/review/`, {
        action,
        notes: matchNotes,
        alternative_target_id: altId,
      });
      setSelectedMatch(null);
      loadMatches();
    } catch (e) {
      alert(e?.response?.data?.detail || "Action failed.");
    } finally {
      setMatchBusy(false);
    }
  }

  async function resolveConflict(action) {
    if (!selectedConflict) return;
    setConflictBusy(true);
    try {
      await api.post(`/conflicts/${selectedConflict.id}/resolve/`, { action, reason: conflictReason });
      setSelectedConflict(null);
      loadConflicts();
    } catch (e) {
      alert(e?.response?.data?.detail || "Action failed.");
    } finally {
      setConflictBusy(false);
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold text-ink-900 mb-1">Human Review Queue</h1>
          <p className="text-sm text-ink-500">
            Review uncertain parcel correspondence candidates, verify split/merge relationships, and resolve geospatial discrepancies.
            {runId ? ` Showing results from run #${runId}.` : ""}
          </p>
        </div>
        <div className="flex bg-ink-100 p-1 rounded-md text-xs font-medium">
          <button
            onClick={() => setActiveTab("matches")}
            className={`px-3 py-1.5 rounded ${activeTab === "matches" ? "bg-white text-ink-900 shadow-sm" : "text-ink-600 hover:text-ink-900"}`}
          >
            Candidate Matches ({matches.length})
          </button>
          <button
            onClick={() => setActiveTab("conflicts")}
            className={`px-3 py-1.5 rounded ${activeTab === "conflicts" ? "bg-white text-ink-900 shadow-sm" : "text-ink-600 hover:text-ink-900"}`}
          >
            Spatial Conflicts ({conflicts.length})
          </button>
        </div>
      </div>

      {activeTab === "matches" ? (
        <div className="flex gap-6">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-medium text-ink-600">Filter by Classification:</div>
              <div className="flex gap-1.5">
                {["ALL", "REVIEW", "SPLIT", "MERGE", "MATCH", "NO_MATCH"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st === "ALL" ? "" : st)}
                    className={`text-xs px-2.5 py-1 rounded border ${
                      (statusFilter === st || (st === "ALL" && !statusFilter))
                        ? "bg-brand-50 border-brand-500 text-brand-700 font-semibold"
                        : "border-ink-200 text-ink-600 hover:bg-ink-50"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-ink-50 text-ink-500 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-4 py-2.5">ID</th>
                    <th className="text-left px-4 py-2.5">Source (A)</th>
                    <th className="text-left px-4 py-2.5">Target (B)</th>
                    <th className="text-left px-4 py-2.5">Relationship</th>
                    <th className="text-left px-4 py-2.5">Confidence</th>
                    <th className="text-left px-4 py-2.5">IoU</th>
                    <th className="text-left px-4 py-2.5">Status</th>
                    <th className="text-left px-4 py-2.5">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {matches.map((m) => (
                    <tr
                      key={m.id}
                      className={`border-t border-ink-100 hover:bg-ink-50 cursor-pointer ${
                        selectedMatch?.id === m.id ? "bg-brand-50/50" : ""
                      }`}
                      onClick={() => openMatch(m.id)}
                    >
                      <td className="px-4 py-2.5 font-medium text-ink-700">#{m.id}</td>
                      <td className="px-4 py-2.5 font-medium text-ink-900">
                        {m.source_parcel_ref || `P-${m.source_parcel}`}
                        <div className="text-[11px] text-ink-400">{m.source_dataset_name}</div>
                      </td>
                      <td className="px-4 py-2.5 font-medium text-ink-900">
                        {m.target_parcel_ref || `P-${m.target_parcel}`}
                        <div className="text-[11px] text-ink-400">{m.target_dataset_name}</div>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                          m.relationship_type === "SPLIT" ? "bg-purple-100 text-purple-800" :
                          m.relationship_type === "MERGE" ? "bg-indigo-100 text-indigo-800" : "bg-ink-100 text-ink-700"
                        }`}>
                          {m.relationship_type}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-semibold text-ink-800">{m.overall_confidence.toFixed(1)}%</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{m.overlap_ratio?.toFixed(2)}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                          m.status === "MATCH" || m.status === "MATCHED" ? "bg-green-100 text-green-800" :
                          m.status === "REVIEW" ? "bg-amber-100 text-amber-800" : "bg-ink-100 text-ink-600"
                        }`}>
                          {m.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-brand-600 text-xs font-medium">Inspect →</td>
                    </tr>
                  ))}
                  {matches.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-ink-400">
                        No candidate matches found for this filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Side Panel for Selected Match */}
          {selectedMatch && (
            <div className="w-[450px] card p-5 h-fit sticky top-6 space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="border-b border-ink-100 pb-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-ink-500 uppercase">Candidate Match #{selectedMatch.id}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-brand-100 text-brand-800 font-semibold">
                    {selectedMatch.relationship_type}
                  </span>
                </div>
                <div className="text-xl font-bold text-ink-900 mt-1">
                  Confidence: {selectedMatch.overall_confidence.toFixed(1)}%
                </div>
              </div>

              {/* Side-by-Side Attributes Comparison */}
              <div>
                <div className="text-xs font-semibold text-ink-700 uppercase tracking-wider mb-2">
                  Side-by-Side Attributes
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-ink-50 p-2.5 rounded border border-ink-200">
                    <div className="font-semibold text-ink-800 border-b border-ink-200 pb-1 mb-1.5">
                      Dataset A ({selectedMatch.source_parcel_detail?.dataset_name || "Source"})
                    </div>
                    <div className="space-y-1 text-ink-700">
                      <div><span className="text-ink-400">ID:</span> <span className="font-mono">{selectedMatch.source_parcel_detail?.parcel_id}</span></div>
                      <div><span className="text-ink-400">Survey No:</span> {selectedMatch.source_parcel_detail?.survey_number || "—"}</div>
                      <div><span className="text-ink-400">Land Use:</span> {selectedMatch.source_parcel_detail?.land_use || "—"}</div>
                      <div><span className="text-ink-400">Area:</span> {selectedMatch.source_parcel_detail?.area ? `${selectedMatch.source_parcel_detail.area.toFixed(1)} m²` : "—"}</div>
                    </div>
                  </div>

                  <div className="bg-ink-50 p-2.5 rounded border border-ink-200">
                    <div className="font-semibold text-ink-800 border-b border-ink-200 pb-1 mb-1.5">
                      Dataset B ({selectedMatch.target_parcel_detail?.dataset_name || "Target"})
                    </div>
                    <div className="space-y-1 text-ink-700">
                      <div><span className="text-ink-400">ID:</span> <span className="font-mono">{selectedMatch.target_parcel_detail?.parcel_id}</span></div>
                      <div><span className="text-ink-400">Survey No:</span> {selectedMatch.target_parcel_detail?.survey_number || "—"}</div>
                      <div><span className="text-ink-400">Land Use:</span> {selectedMatch.target_parcel_detail?.land_use || "—"}</div>
                      <div><span className="text-ink-400">Area:</span> {selectedMatch.target_parcel_detail?.area ? `${selectedMatch.target_parcel_detail.area.toFixed(1)} m²` : "—"}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Spatial Metrics Breakdown */}
              <div>
                <div className="text-xs font-semibold text-ink-700 uppercase tracking-wider mb-2">
                  Measured Spatial Metrics
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">IoU (Overlap)</div>
                    <div className="font-bold text-ink-900">{selectedMatch.overlap_ratio?.toFixed(2)}</div>
                  </div>
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">Centroid Dist</div>
                    <div className="font-bold text-ink-900">{selectedMatch.centroid_distance_m?.toFixed(1)}m</div>
                  </div>
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">Area Sim</div>
                    <div className="font-bold text-ink-900">{(selectedMatch.area_similarity * 100)?.toFixed(0)}%</div>
                  </div>
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">Shape Sim</div>
                    <div className="font-bold text-ink-900">{(selectedMatch.shape_similarity * 100)?.toFixed(0)}%</div>
                  </div>
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">Boundary Sim</div>
                    <div className="font-bold text-ink-900">{(selectedMatch.boundary_similarity * 100)?.toFixed(0)}%</div>
                  </div>
                  <div className="p-2 bg-ink-50 rounded text-center">
                    <div className="text-ink-400 text-[10px]">Topology</div>
                    <div className="font-bold text-ink-900 truncate">{selectedMatch.topology_relationship}</div>
                  </div>
                </div>
              </div>

              {/* Explainable Reasons */}
              {selectedMatch.reasons && selectedMatch.reasons.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-ink-700 uppercase tracking-wider mb-1.5">
                    Explainable Assessment
                  </div>
                  <ul className="text-xs space-y-1 text-ink-600 bg-amber-50/50 p-2.5 rounded border border-amber-200">
                    {selectedMatch.reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-amber-500">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Alternative Candidates */}
              {selectedMatch.alternatives && selectedMatch.alternatives.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-ink-700 uppercase tracking-wider mb-1.5">
                    Alternative Candidates for Source
                  </div>
                  <div className="space-y-1.5">
                    {selectedMatch.alternatives.map((alt) => (
                      <div key={alt.match_id} className="p-2 bg-ink-50 rounded border border-ink-200 flex items-center justify-between text-xs">
                        <div>
                          <span className="font-mono font-medium">{alt.target_parcel_ref}</span>
                          <span className="text-ink-400 ml-1.5">({alt.confidence.toFixed(1)}%)</span>
                        </div>
                        <button
                          onClick={() => resolveMatch("CHOOSE_ALTERNATIVE", alt.target_parcel_id)}
                          className="text-xs text-brand-600 hover:underline font-semibold"
                        >
                          Select Alternative →
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Review Decision Notes */}
              <div>
                <label className="block text-xs font-medium text-ink-600 mb-1">Decision Notes / Audit Reason</label>
                <textarea
                  className="w-full border border-ink-200 rounded-md px-3 py-2 text-xs"
                  placeholder="Officer review justification (persisted in audit trail)..."
                  value={matchNotes}
                  onChange={(e) => setMatchNotes(e.target.value)}
                  rows={2}
                />
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-ink-100">
                {MATCH_ACTIONS.map((a) => (
                  <button
                    key={a.key}
                    disabled={matchBusy}
                    onClick={() => resolveMatch(a.key)}
                    className={`text-xs py-2 px-2.5 rounded font-medium border text-center transition ${a.style}`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Conflicts Tab */
        <div className="flex gap-6">
          <div className="flex-1">
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-ink-50 text-ink-500 text-xs uppercase">
                  <tr>
                    <th className="text-left px-4 py-2.5">Conflict ID</th>
                    <th className="text-left px-4 py-2.5">Parcel</th>
                    <th className="text-left px-4 py-2.5">Type</th>
                    <th className="text-left px-4 py-2.5">Measured Difference</th>
                    <th className="text-left px-4 py-2.5">Severity</th>
                    <th className="text-left px-4 py-2.5">Status</th>
                    <th className="text-left px-4 py-2.5">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {conflicts.map((c) => (
                    <tr
                      key={c.id}
                      className="border-t border-ink-100 hover:bg-ink-50 cursor-pointer"
                      onClick={() => openConflict(c.id)}
                    >
                      <td className="px-4 py-2.5 font-medium text-ink-700">#{c.id}</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{c.parcel_a_ref || "—"}</td>
                      <td className="px-4 py-2.5">{c.conflict_type.replace(/_/g, " ")}</td>
                      <td className="px-4 py-2.5 text-xs font-mono">{JSON.stringify(c.measured_difference)}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                          c.severity === "CRITICAL" ? "bg-red-100 text-red-800" :
                          c.severity === "HIGH" ? "bg-amber-100 text-amber-800" : "bg-ink-100 text-ink-700"
                        }`}>
                          {c.severity}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-xs">{c.status}</td>
                      <td className="px-4 py-2.5 text-brand-600 text-xs font-medium">Review →</td>
                    </tr>
                  ))}
                  {conflicts.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-ink-400">
                        No pending spatial conflicts.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {selectedConflict && (
            <div className="w-96 card p-5 h-fit sticky top-6 space-y-3">
              <div className="border-b border-ink-100 pb-2">
                <span className="text-xs font-mono font-bold text-ink-500 uppercase">Conflict #{selectedConflict.id}</span>
                <div className="text-base font-semibold text-ink-900 mt-0.5">
                  {selectedConflict.conflict_type.replace(/_/g, " ")}
                </div>
              </div>
              <div className="text-xs text-ink-700">{selectedConflict.description}</div>
              <div className="bg-ink-50 p-2.5 rounded text-xs text-ink-700">
                <span className="text-ink-400 block mb-0.5">Suggested Action:</span>
                <span className="font-medium">{selectedConflict.suggested_resolution || "Officer evaluation required"}</span>
              </div>
              <div>
                <label className="block text-xs font-medium text-ink-600 mb-1">Resolution Notes</label>
                <textarea
                  className="w-full border border-ink-200 rounded px-2.5 py-1.5 text-xs"
                  placeholder="Resolution reason..."
                  value={conflictReason}
                  onChange={(e) => setConflictReason(e.target.value)}
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-ink-100">
                {[
                  { key: "ACCEPT", label: "Accept Source A" },
                  { key: "KEEP_EXISTING", label: "Keep Source B" },
                  { key: "FIELD_VERIFICATION", label: "Field Survey" },
                  { key: "REJECT", label: "Reject Both" },
                ].map((act) => (
                  <button
                    key={act.key}
                    disabled={conflictBusy}
                    onClick={() => resolveConflict(act.key)}
                    className="btn-secondary text-xs py-1.5"
                  >
                    {act.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
