"use client";

import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { User, AuthContextType, Document } from "@/types";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_STORAGE_KEY = "sentinel-auth-token";

interface BackendUser {
  id: number;
  email: string;
  username: string;
  rbac_level: "admin" | "manager" | "analyst";
  manager_id?: number | null;
  created_by?: number | null;
}

function mapBackendUser(payload: BackendUser): User {
  return {
    id: String(payload.id),
    email: payload.email,
    name: payload.username,
    rbacLevel: payload.rbac_level,
    managerId: payload.manager_id ?? null,
    createdBy: payload.created_by ?? null,
  };
}

async function request<T>(
  input: RequestInfo,
  init: RequestInit = {}
): Promise<T> {
  const response = await fetch(input, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorMessage = data?.detail ?? "Request failed";
    throw new Error(
      typeof errorMessage === "string"
        ? errorMessage
        : JSON.stringify(errorMessage)
    );
  }
  return data as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [token, setToken] = useState<string | null>(null);

  const persistToken = useCallback((value: string | null) => {
    setToken(value);
    if (typeof window === "undefined") return;

    if (value) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }, []);

  const fetchProfile = useCallback(async (accessToken: string) => {
    const profile = await request<BackendUser>(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    setUser(mapBackendUser(profile));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!storedToken) return;

    persistToken(storedToken);
    fetchProfile(storedToken).catch(() => {
      persistToken(null);
      setUser(null);
    });
  }, [fetchProfile, persistToken]);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await request<{ access_token: string }>(
        `${API_BASE_URL}/auth/login`,
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }
      );
      persistToken(result.access_token);
      await fetchProfile(result.access_token);
      setDocuments([]); // Clear cached documents; fetch when dashboard loads
    },
    [fetchProfile, persistToken]
  );

  const signup = useCallback(
    async (data: {
      email: string;
      username: string;
      password: string;
      rbacLevel: "admin" | "manager" | "analyst";
      managerId?: number;
    }) => {
      await request(`${API_BASE_URL}/auth/signup`, {
        method: "POST",
        body: JSON.stringify({
          email: data.email,
          username: data.username,
          password: data.password,
          rbac_level: data.rbacLevel,
          manager_id: data.managerId,
        }),
      });
      await login(data.email, data.password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    if (!token) {
      setUser(null);
      setDocuments([]);
      persistToken(null);
      return;
    }

    try {
      await request(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      // Ignore logout errors to avoid trapping the user
      console.warn("Logout failed:", error);
    } finally {
      setUser(null);
      setDocuments([]);
      persistToken(null);
    }
  }, [persistToken, token]);

  const addDocument = useCallback((document: Document) => {
    setDocuments((prev) => [document, ...prev]);
  }, []);

  const contextValue = useMemo<AuthContextType>(
    () => ({
      user,
      isAuthenticated: !!user,
      login,
      signup,
      logout,
      documents,
      addDocument,
    }),
    [addDocument, documents, login, logout, signup, user]
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
