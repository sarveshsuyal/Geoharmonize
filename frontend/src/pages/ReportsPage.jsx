import React from "react";
import { API_BASE_URL } from "../services/api.js";

const REPORTS = [
  { label: "Conflict Report (CSV)", path: "/reports/conflicts/" },
  { label: "Dataset Validation Report (CSV)", path: "/reports/dataset-validation/" },
  { label: "Parcel Matching Report (CSV)", path: "/reports/parcel-matching/" },
];

export default function ReportsPage() {
  const baseURL = API_BASE_URL;
  const token = localStorage.getItem("gh_access_token");

  function download(path) {
    // Simple approach for the MVP: open in a new tab with the token as a query
    // param is avoided (tokens shouldn't go in URLs) - instead we fetch and
    // trigger a blob download using the stored bearer token.
    fetch(`${baseURL}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.blob())
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = path.split("/").filter(Boolean).pop() + ".csv";
        a.click();
        window.URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Reports</h1>
      <p className="text-sm text-ink-500 mb-4">Generated directly from the current database state.</p>
      <div className="card divide-y divide-ink-100">
        {REPORTS.map((r) => (
          <button key={r.path} onClick={() => download(r.path)} className="w-full text-left px-4 py-3 text-sm text-ink-700 hover:bg-ink-50">
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );
}
