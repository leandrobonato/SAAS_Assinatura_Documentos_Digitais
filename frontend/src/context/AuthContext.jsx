import { createContext, useCallback, useContext, useEffect, useState } from "react";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem("docuflow_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("docuflow_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  function applySession(payload) {
    localStorage.setItem("docuflow_token", payload.access_token);
    setUser(payload.user);
  }

  async function login(email, password) {
    const { data } = await api.post("/auth/login", { email, password });
    applySession(data);
  }

  async function register(name, email, password) {
    const { data } = await api.post("/auth/register", { name, email, password });
    applySession(data);
  }

  function logout() {
    localStorage.removeItem("docuflow_token");
    setUser(null);
  }

  async function togglePlan() {
    const nextPlan = user.plan === "free" ? "pro" : "free";
    const { data } = await api.patch("/auth/me/plan", { plan: nextPlan });
    setUser(data);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, togglePlan, refresh: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
