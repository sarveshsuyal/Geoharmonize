import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import {
  GitMerge,
  Download,
  CheckCircle2,
  RefreshCw,
  Play,
  ArrowRight,
  Clock,
  Layers,
  Map as MapIcon,
  AlertTriangle,
  FileCheck,
} from "lucide-react";

const STEP_LABELS = [
  "DATA_INGESTION",
  "CRS_NORMALIZATION",
  "GEOMETRY_VALIDATION",
  "SPATIAL_MATCHING",
  "ATTRIBUTE_HARMONIZATION",
  "TOPOLOGY_VALIDATION",
  "CONFLICT_DETECTION",
  "CONFIDENCE_SCORING",
  "HARMONIZED_MAP_GENERATION",
];

export default function HarmonizationPage() {
  const [datasets, setDatasets] = useState([]);
  const [selected, setSelected] = useState([]);
  const [running, setRunning] = useState(false);
  const [runs, setRuns] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [exportingId, setExportingId] = useState(null);

  function load() {
    api.get("/datasets/").then((res) => setDatasets(res.data.results || res.data));
    api.get("/harmonization/runs/").then((res) => setRuns(res.data.results || res.data));
  }

  useEffect(() => {
    load();
  }, []);

  function toggle(id) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function startRun() {
    if (selected.length < 2) {
      setError("Please select at least two datasets to harmonize (e.g. Cadastral Survey and Drone Imagery).");
      return;
    }
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post("/harmonization/run/", { dataset_ids: selected });
      setResult(res.data);
      await pollRun(res.data.id);
    } catch (e) {
      const details = e?.response?.data;
      setError(details?.dataset_ids?.[0] || details?.detail || details?.error || "Harmonization run failed.");
    } finally {
      setRunning(false);
    }
  }

  async function pollRun(runId) {
    let current = result;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const response = await api.get(`/harmonization/runs/${runId}/`);
      current = response.data;
      setResult(current);
      if (["COMPLETED", "FAILED"].includes(current.status)) {
        if (current.status === "FAILED") {
          setError(current.error_message || "Harmonization run failed.");
        }
        load();
        return current;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
    throw new Error("Harmonization run did not finish within the polling window.");
  }

  async function downloadExport(runId) {
    setExportingId(runId);
    try {
      const res = await api.get(`/harmonization/runs/${runId}/export/`, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/geo+json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `harmonized_run_${runId}.geojson`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to download harmonized GeoJSON.");
    } finally {
      setExportingId(null);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Spatial Harmonization Pipeline</h1>
        <p className="text-xs text-slate-500 mt-1">
          Perform multi-source topological indexing (STRtree), measured IoU matching, attribute unification,
          split/merge classification, and explainable confidence scoring.
        </p>
      </div>

      {/* Dataset Selection Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-600" />
            <h2 className="text-base font-bold text-slate-900">Select Datasets to Reconcile</h2>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {selected.length} layer{selected.length === 1 ? "" : "s"} selected
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {datasets.map((d) => (
            <label
              key={d.id}
              className={`flex items-start gap-3 p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                selected.includes(d.id)
                  ? "border-sky-500 bg-sky-50/50 shadow-sm"
                  : "border-slate-200 hover:border-slate-300 hover:bg-slate-50/40"
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 rounded text-sky-600 focus:ring-sky-500"
                checked={selected.includes(d.id)}
                onChange={() => toggle(d.id)}
              />
              <div className="min-w-0">
                <div className="font-semibold text-slate-900 truncate">{d.name}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Type: <span className="font-mono text-slate-700">{d.dataset_type}</span> · Features:{" "}
                  <strong>{d.feature_count ?? "—"}</strong> · CRS: {d.original_crs || "Not set"}
                </div>
              </div>
            </label>
          ))}

          {datasets.length === 0 && (
            <div className="col-span-2 text-xs text-slate-400 py-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
              No datasets available. Please{" "}
              <Link to="/upload" className="text-sky-600 font-semibold underline">
                upload layers
              </Link>{" "}
              or run the demo from Dashboard.
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-100">
          <div className="text-xs text-slate-500">
            Select 2+ layers to compute boundary intersections and attribute reconciliation.
          </div>
          <button
            onClick={startRun}
            disabled={running || selected.length < 2}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition-colors disabled:opacity-50"
          >
            {running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Executing Pipeline Stages...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Run Harmonization Pipeline</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Running Stages Animation */}
      {running && (
        <div className="bg-sky-50/60 border border-sky-200 rounded-2xl p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-sky-950">
            <RefreshCw className="w-4 h-4 text-sky-600 animate-spin" />
            <span>Running Automated Geospatial Pipeline...</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2 text-[10px]">
            {STEP_LABELS.map((step, idx) => (
              <div
                key={step}
                className="p-2 rounded-lg bg-white border border-sky-100 text-slate-700 flex items-center gap-1.5 shadow-2xs"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
                <span className="truncate">{step.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Run Result Card */}
      {result && (
        <div className="bg-emerald-50/60 border border-emerald-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <span className="font-bold text-emerald-950 text-base">
                Harmonization Run #{result.id} — {result.status}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => downloadExport(result.id)}
                disabled={exportingId === result.id}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs shadow-sm transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>{exportingId === result.id ? "Exporting..." : "Download Harmonized GeoJSON"}</span>
              </button>
              <Link
                to={`/review?run=${result.id}`}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
              >
                <span>Review Queue</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>
              <Link
                to="/map"
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
              >
                <MapIcon className="w-3.5 h-3.5 text-sky-600" />
                <span>View on Map</span>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 text-xs">
            {Object.entries(result.statistics || {}).map(([key, val]) => (
              <div key={key} className="bg-white p-3 rounded-xl border border-emerald-100 shadow-2xs">
                <div className="text-[10px] text-slate-400 capitalize">{key.replace(/_/g, " ")}</div>
                <div className="text-base font-bold text-slate-900 mt-0.5">{val}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Run History */}
      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-500" />
          <span>Harmonization Run History</span>
        </h2>

        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-5 py-3">Run ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Datasets Reconciled</th>
                  <th className="px-4 py-3">Matched Parcels</th>
                  <th className="px-4 py-3">Officer Review</th>
                  <th className="px-4 py-3">Split / Merge</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((r) => {
                  const s = r.statistics || {};
                  return (
                    <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-5 py-3 font-mono font-bold text-slate-900">#{r.id}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            r.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-sky-50 text-sky-700 border-sky-200"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {(r.dataset_ids || []).join(", ")}
                      </td>
                      <td className="px-4 py-3 font-bold text-emerald-700">{s.matched ?? "—"}</td>
                      <td className="px-4 py-3 font-semibold text-amber-700">{s.review ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {s.split || 0} / {s.merge || 0}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-[11px]">
                        {new Date(r.started_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3 text-right space-x-2">
                        <button
                          onClick={() => downloadExport(r.id)}
                          disabled={exportingId === r.id}
                          className="text-xs font-semibold text-sky-600 hover:text-sky-800"
                        >
                          {exportingId === r.id ? "Exporting..." : "Export GeoJSON"}
                        </button>
                        <Link
                          to={`/review?run=${r.id}`}
                          className="text-xs font-semibold text-slate-600 hover:text-slate-900"
                        >
                          Review
                        </Link>
                      </td>
                    </tr>
                  );
                })}

                {runs.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-6 py-10 text-center text-slate-400">
                      No harmonization runs executed yet. Select datasets above and launch the pipeline.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
