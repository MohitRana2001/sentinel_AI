"use client"

import type React from "react"
import { createContext, useContext, useState } from "react"
import type { User, AuthContextType, UserRole, Document } from "@/types"

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Dummy credentials database
const DUMMY_USERS: Record<string, { password: string; role: UserRole; name: string }> = {
  "admin@test.com": { password: "password", role: "admin", name: "Admin User" },
  "analyst@test.com": { password: "password", role: "analyst", name: "Analyst User" },
  "manager@test.com": { password: "password", role: "manager", name: "Manager User" },
  "super_admin@test.com": { password: "password", role: "super_admin", name: "Super Admin User" },
}

const DUMMY_DOCUMENTS: Document[] = [
  {
    id: "doc-001",
    fileName: "quarterly-report.pdf",
    uploadedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    fileSize: 2.5,
    status: "completed",
  },
  {
    id: "doc-002",
    fileName: "annual-summary.docx",
    uploadedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    fileSize: 1.8,
    status: "completed",
  },
  {
    id: "doc-003",
    fileName: "market-analysis.xlsx",
    uploadedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    fileSize: 3.2,
    status: "completed",
  },
  {
    id: "doc-004",
    fileName: "presentation.pptx",
    uploadedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    fileSize: 5.1,
    status: "completed",
  },
]

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])

  const login = (email: string, password: string): boolean => {
    const credentials = DUMMY_USERS[email]
    if (credentials && credentials.password === password) {
      setUser({
        id: `user-${Date.now()}`,
        email,
        role: credentials.role,
        name: credentials.name,
      })
      setDocuments(DUMMY_DOCUMENTS)
      return true
    }
    return false
  }

  const logout = () => {
    setUser(null)
    setDocuments([])
  }

  const addDocument = (document: Document) => {
    setDocuments((prev) => [document, ...prev])
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, documents, addDocument }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
