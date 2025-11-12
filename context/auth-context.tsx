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

import type { User, AuthContextType, Document, MediaItem, MediaType } from "@/types";

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
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
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

  // NEW: Upload media (document/audio/video)
  const uploadMedia = useCallback(async (file: File, mediaType: MediaType, language?: string) => {
    if (!token) {
      throw new Error("Not authenticated");
    }

    const formData = new FormData();
    formData.append('files', file);  // Changed from 'file' to 'files' (backend expects List[UploadFile])
    formData.append('media_type', mediaType);
    
    // For audio/video, send the language code
    if (language && (mediaType === 'audio' || mediaType === 'video')) {
      formData.append('language', language);
    }

    const response = await fetch(`${API_BASE_URL}/upload`, {  // Changed from /media/upload to /upload
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        // Don't set Content-Type - let browser set it with boundary for multipart/form-data
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    const { job_id, status } = await response.json();  // Backend returns job_id, not media_id

    // Add to local state immediately
    const newItem: MediaItem = {
      id: job_id,  // Use job_id as the media item id
      fileName: file.name,
      mediaType,
      uploadedAt: new Date().toISOString(),
      fileSize: file.size / 1024 / 1024,
      status: 'queued',
      jobId: job_id,
      language,
      progress: 0
    };

    setMediaItems(prev => [newItem, ...prev]);

    // Start polling for status
    pollJobStatus(job_id, job_id);  // Use job_id for both
  }, [token]);

  // NEW: Poll job status every 2 seconds
  const pollJobStatus = useCallback(async (jobId: string, mediaId: string) => {
    if (!token) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/jobs/${encodeURIComponent(jobId)}/status`, {  // Use /jobs/{job_id}/status
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });

        if (!response.ok) {
          clearInterval(interval);
          return;
        }

        const { status, progress_percentage, error_message } = await response.json();

        setMediaItems(prev => prev.map(item => 
          item.id === mediaId 
            ? { 
                ...item, 
                status: status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : status === 'processing' ? 'processing' : 'queued',
                progress: progress_percentage || 0,
                // summary and transcription will come from results endpoint
              }
            : item
        ));

        if (status === 'completed' || status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error polling status:', error);
        clearInterval(interval);
      }
    }, 2000);
  }, [token]);

  // NEW: Unified upload for multiple media types + suspects in one job
  const uploadJob = useCallback(async (job: { files: any[]; suspects: any[] }) => {
    if (!token) {
      throw new Error("Not authenticated");
    }

    const formData = new FormData();
    
    // Add all files with their metadata
    job.files.forEach((fileWithMeta, index) => {
      formData.append('files', fileWithMeta.file);
      formData.append(`media_types`, fileWithMeta.mediaType);
      if (fileWithMeta.language) {
        formData.append(`languages`, fileWithMeta.language);
      } else {
        formData.append(`languages`, '');  // Empty string for files without language
      }
    });

    // Add suspects data as JSON
    if (job.suspects.length > 0) {
      formData.append('suspects', JSON.stringify(job.suspects));
    }

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    const { job_id, status } = await response.json();

    // Add all files to mediaItems state
    job.files.forEach((fileWithMeta) => {
      const newItem: MediaItem = {
        id: `${job_id}-${fileWithMeta.file.name}`,
        fileName: fileWithMeta.file.name,
        mediaType: fileWithMeta.mediaType,
        uploadedAt: new Date().toISOString(),
        fileSize: fileWithMeta.file.size / 1024 / 1024,
        status: 'queued',
        jobId: job_id,
        language: fileWithMeta.language,
        progress: 0
      };
      setMediaItems(prev => [newItem, ...prev]);
    });

    // Start polling for status
    pollJobStatus(job_id, job_id);
  }, [token]);

  const contextValue = useMemo<AuthContextType>(
    () => ({
      user,
      isAuthenticated: !!user,
      login,
      signup,
      logout,
      documents,
      mediaItems,
      addDocument,
      uploadMedia,
      uploadJob,
    }),
    [addDocument, documents, mediaItems, login, logout, signup, uploadMedia, uploadJob, user]
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
