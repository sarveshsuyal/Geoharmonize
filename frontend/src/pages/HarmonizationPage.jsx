import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const STEP_LABELS = [
  "DATA_INGESTION", "CRS_NORMALIZATION", "GEOMETRY_VALIDATION", "SPATIAL_MATCHING",
  "ATTRIBUTE_HARMONIZATION", "TOPOLOGY_VALIDATION", "CONFLICT_DETECTION",
  "CONFIDENCE_SCORING", "HARMONIZED_MAP_GENERATION",
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
        if (current.status === "FAILED") setError(current.error_message || "Harmonization run failed.");
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
    <div className="p-6 max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900 mb-1">Harmonization Pipeline</h1>
        <p className="text-sm text-ink-500">
          Select two or more datasets to run full spatial candidate indexing (STRtree), geometry validation,
          dynamic attribute matching, split/merge detection, and explainable confidence scoring.
        </p>
      </div>

      <div className="card p-5">
        <div className="text-sm font-semibold text-ink-800 mb-2">Select Datasets to Harmonize</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          {datasets.map((d) => (
            <label
              key={d.id}
              className={`flex items-start gap-3 p-3 rounded border text-sm cursor-pointer transition ${
                selected.includes(d.id) ? "border-brand-500 bg-brand-50/30" : "border-ink-200 hover:border-ink-300"
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5"
                checked={selected.includes(d.id)}
                onChange={() => toggle(d.id)}
              />
              <div>
                <div className="font-medium text-ink-900">{d.name}</div>
                <div className="text-xs text-ink-500">
                  Type: {d.dataset_type} · Features: {d.feature_count ?? "—"} · CRS: {d.original_crs || "Not set"}
                </div>
              </div>
            </label>
          ))}
          {datasets.length === 0 && (
            <div className="col-span-2 text-sm text-ink-400 py-4">
              No datasets available. Please <Link to="/upload" className="text-brand-600 underline">upload datasets</Link> first.
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={startRun} disabled={running || selected.length < 2} className="btn-primary">
            {running ? "Processing Harmonization..." : "Run Harmonization Pipeline"}
          </button>
          <span className="text-xs text-ink-500">
            {selected.length} dataset{selected.length === 1 ? "" : "s"} selected
          </span>
        </div>
        {error && <div className="text-sm text-status-low mt-3 font-medium">{error}</div>}
      </div>

      {running && (
        <div className="card p-5 border-brand-200 bg-brand-50/10">
          <div className="text-sm font-semibold text-ink-800 mb-3 flex items-center gap-2">
            <span className="animate-spin text-brand-600">⟳</span> Running Processing Stages...
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {STEP_LABELS.map((s) => (
              <div key={s} className="p-2 rounded bg-white border border-ink-100 flex items-center gap-2 text-ink-700">
                <span className="text-brand-500 font-bold">•</span>
                <span>{s.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="card p-5 border-green-300 bg-green-50/20">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-status-high">
              {result.status === "COMPLETED" ? "✓" : ""} Harmonization Run #{result.id} — {result.status}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => downloadExport(result.id)}
                disabled={exportingId === result.id}
                className="btn-primary text-xs flex items-center gap-1.5"
              >
                <span>⬇</span>
                {exportingId === result.id ? "Exporting..." : "Download Harmonized GeoJSON"}
              </button>
              <Link to={`/review?run=${result.id}`} className="btn-secondary text-xs">
                Open Review Queue →
              </Link>
              <Link to="/map" className="btn-secondary text-xs">
                View on Map
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 text-xs pt-1">
            {Object.entries(result.statistics || {}).map(([k, v]) => (
              <div key={k} className="bg-white p-2.5 rounded border border-ink-100 shadow-sm">
                <div className="text-ink-400 capitalize">{k.replace(/_/g, " ")}</div>
                <div className="text-base font-bold text-ink-800">{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="text-sm font-semibold text-ink-800 mb-2">Processing Run History</div>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-50 text-ink-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-2.5">Run ID</th>
                <th className="text-left px-4 py-2.5">Status</th>
                <th className="text-left px-4 py-2.5">Datasets</th>
                <th className="text-left px-4 py-2.5">Matched</th>
                <th className="text-left px-4 py-2.5">Review</th>
                <th className="text-left px-4 py-2.5">Split / Merge</th>
                <th className="text-left px-4 py-2.5">Timestamp</th>
                <th className="text-left px-4 py-2.5">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const s = r.statistics || {};
                return (
                  <tr key={r.id} className="border-t border-ink-100 hover:bg-ink-50">
                    <td className="px-4 py-2.5 font-medium text-ink-800">#{r.id}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        r.status === "COMPLETED" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-ink-600">{(r.dataset_ids || []).join(", ")}</td>
                    <td className="px-4 py-2.5 font-semibold text-green-700">{s.matched ?? "—"}</td>
                    <td className="px-4 py-2.5 text-amber-700">{s.review ?? "—"}</td>
                    <td className="px-4 py-2.5 text-ink-700">
                      {s.split || 0} / {s.merge || 0}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-ink-500">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 space-x-2">
                      <button
                        onClick={() => downloadExport(r.id)}
                        disabled={exportingId === r.id}
                        className="text-xs text-brand-600 hover:underline font-medium"
                      >
                        {exportingId === r.id ? "Exporting..." : "Export GeoJSON"}
                      </button>
                      <Link to={`/review?run=${r.id}`} className="text-xs text-ink-600 hover:underline">
                        Review
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-ink-400">
                    No harmonization runs yet. Select datasets and run the pipeline above.
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
