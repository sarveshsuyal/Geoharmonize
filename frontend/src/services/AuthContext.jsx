import React, { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("gh_access_token");
    if (!token) {
      const offlineUser = localStorage.getItem("gh_offline_user");
      if (offlineUser) {
        try {
          setUser(JSON.parse(offlineUser));
        } catch {
          localStorage.removeItem("gh_offline_user");
        }
      }
      setLoading(false);
      return;
    }
    api
      .get("/auth/me/")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("gh_access_token");
        const offlineUser = localStorage.getItem("gh_offline_user");
        if (offlineUser) {
          try {
            setUser(JSON.parse(offlineUser));
          } catch {
            localStorage.removeItem("gh_offline_user");
          }
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    try {
      const res = await api.post("/auth/login/", { username, password });
      localStorage.setItem("gh_access_token", res.data.access);
      localStorage.removeItem("gh_offline_user");
      setUser(res.data.user);
      return res.data.user;
    } catch (err) {
      // If the backend Docker container is offline or starting up,
      // allow instant sign-in for the designated administrator account
      const isDockerOffline = !err.response;
      const trimmedUser = (username || "").trim().toLowerCase();
      const isMatchingCreds =
        (trimmedUser === "sarvesh" || trimmedUser === "sarvesh112k@gmail.com") &&
        password === "sarvesh@suyal";

      if (isDockerOffline && isMatchingCreds) {
        const fallbackUser = {
          id: 1,
          username: "sarvesh",
          email: "sarvesh112k@gmail.com",
          role: "ADMIN",
          organization: "Department of Land Resources",
          designation: "Administrator",
          first_name: "Sarvesh",
          last_name: "Suyal",
          is_offline_demo: true,
        };
        localStorage.setItem("gh_offline_user", JSON.stringify(fallbackUser));
        setUser(fallbackUser);
        return fallbackUser;
      }
      throw err;
    }
  }

  function logout() {
    localStorage.removeItem("gh_access_token");
    localStorage.removeItem("gh_offline_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
