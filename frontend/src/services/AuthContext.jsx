import React, { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("gh_access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me/")
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem("gh_access_token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const res = await api.post("/auth/login/", { username, password });
    localStorage.setItem("gh_access_token", res.data.access);
    setUser(res.data.user);
    return res.data.user;
  }

  function logout() {
    localStorage.removeItem("gh_access_token");
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
