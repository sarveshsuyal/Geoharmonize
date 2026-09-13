import React, { useEffect, useState } from "react";
import api from "../services/api";

const STATUS_TONE = {
  PROCESSED: "status-badge-high", VALIDATED: "status-badge-high",
  NEEDS_CRS: "status-badge-medium", PROCESSING: "status-badge-medium", VALIDATING: "status-badge-medium",
  FAILED: "status-badge-low", UPLOADED: "status-badge-medium",
};

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [crsPromptFor, setCrsPromptFor] = useState(null);
  const [crsValue, setCrsValue] = useState("EPSG:32644");
  const [busyId, setBusyId] = useState(null);

  function load() {
    api.get("/datasets/").then((res) => setDatasets(res.data.results || res.data));
  }
  useEffect(load, []);

  async function handleProcess(id) {
    setBusyId(id);
    try {
      await api.post(`/datasets/${id}/process/`);
    } catch (e) {
      if (e?.response?.data?.code === "INVALID_CRS") setCrsPromptFor(id);
    } finally {
      setBusyId(null);
      load();
    }
  }

  async function handleSetCrs() {
    await api.post(`/datasets/${crsPromptFor}/set-crs/`, { crs: crsValue });
    setCrsPromptFor(null);
    load();
  }

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Datasets</h1>
      <p className="text-sm text-ink-500 mb-4">All uploaded source datasets and their processing status.</p>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Source</th>
              <th className="text-left px-4 py-2">CRS</th>
              <th className="text-left px-4 py-2">Features</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Uploaded</th>
              <th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id} className="border-t border-ink-100">
                <td className="px-4 py-2 font-medium text-ink-800">{d.name}</td>
                <td className="px-4 py-2">{d.dataset_type}</td>
                <td className="px-4 py-2">{d.source}</td>
                <td className="px-4 py-2">{d.original_crs || <span className="text-status-medium">Not detected</span>}</td>
                <td className="px-4 py-2">{d.feature_count ?? "—"}</td>
                <td className="px-4 py-2">
                  <span className={`status-badge ${STATUS_TONE[d.processing_status] || "status-badge-medium"}`}>
                    {d.processing_status}
                  </span>
                </td>
                <td className="px-4 py-2 text-ink-500">{new Date(d.created_at).toLocaleString()}</td>
                <td className="px-4 py-2 space-x-2">
                  <button
                    onClick={() => handleProcess(d.id)}
                    disabled={busyId === d.id}
                    className="btn-secondary"
                  >
                    {busyId === d.id ? "Processing..." : "Process"}
                  </button>
                </td>
              </tr>
            ))}
            {datasets.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-ink-400">
                  No datasets yet. Upload a file or run the demo generator from the Dashboard.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {crsPromptFor && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center">
          <div className="card bg-white p-5 w-96">
            <div className="font-medium text-ink-800 mb-1">CRS not detected</div>
            <p className="text-xs text-ink-500 mb-3">
              The uploaded dataset does not contain a valid coordinate reference system.
              Please specify the CRS before processing.
            </p>
            <input
              className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm mb-3"
              value={crsValue}
              onChange={(e) => setCrsValue(e.target.value)}
              placeholder="e.g. EPSG:32644"
            />
            <div className="flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setCrsPromptFor(null)}>Cancel</button>
              <button className="btn-primary" onClick={handleSetCrs}>Set CRS</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
