import axios from "axios";

// Default base URL from environment variable or production Render URL
const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD
    ? "https://geoharmonize-backend-8b1m.onrender.com/api"
    : "http://localhost:8000/api");

// Retrieve user-customized API base URL if saved in localStorage
export function getApiBaseUrl() {
  return localStorage.getItem("gh_custom_api_url") || DEFAULT_API_BASE_URL;
}

export function setApiBaseUrl(newUrl) {
  if (!newUrl) {
    localStorage.removeItem("gh_custom_api_url");
  } else {
    // Strip trailing slashes
    let sanitized = newUrl.trim().replace(/\/+$/, "");
    if (!sanitized.endsWith("/api")) {
      sanitized = `${sanitized}/api`;
    }
    localStorage.setItem("gh_custom_api_url", sanitized);
  }
  api.defaults.baseURL = getApiBaseUrl();
}

export const API_BASE_URL = getApiBaseUrl();

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000, // 45s to allow for Render cold starts
});

api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  const token = localStorage.getItem("gh_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear the stale token so ProtectedRoute redirects to /login rather
// than looping on requests that will never succeed.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("gh_access_token");
    }
    return Promise.reject(error);
  }
);

// Diagnostic helper to ping backend health
export async function checkBackendHealth(targetUrl = null) {
  const baseUrl = targetUrl ? targetUrl.replace(/\/+$/, "") : getApiBaseUrl();
  const hostUrl = baseUrl.replace(/\/api$/, "");
  const startTime = Date.now();

  try {
    const res = await axios.get(`${hostUrl}/health/`, { timeout: 15000 });
    const latency = Date.now() - startTime;
    return {
      ok: true,
      latency,
      data: res.data,
      url: baseUrl,
    };
  } catch (err) {
    const latency = Date.now() - startTime;
    return {
      ok: false,
      latency,
      error: err.message,
      status: err.response?.status,
      url: baseUrl,
    };
  }
}

export default api;
