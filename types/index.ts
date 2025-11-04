export interface User {
  id: string
  email: string
  name: string
  rbacLevel: "admin" | "manager" | "analyst"
  managerId?: number | null
  createdBy?: number | null
}

export interface Manager {
  id: number
  email: string
  username: string
  created_at: string
  analysts: Analyst[]
}

export interface Analyst {
  id: number
  email: string
  username: string
  rbac_level: "analyst"
  manager_id: number | null
  created_by: number | null
  created_at: string
}

export interface AnalystWithManager extends Analyst {
  manager_email?: string | null
}

export interface JobWithAnalyst {
  job_id: string
  analyst_email: string
  analyst_username: string
  status: string
  total_files: number
  processed_files: number
  created_at: string
  progress_percentage: number
}

export interface ChartData {
  name: string
  value: number
  category: string
}

export interface DocumentResult {
  id: number
  fileName: string
  uploadedAt: string
  fileType: string
  summary: string
  transcription: string | null
  translation: string | null
  hasAudio: boolean
  isNonEnglish: boolean
}

export interface ChatSource {
  document_id: number
  chunk_index: number
  chunk_text: string
  metadata: Record<string, any>
}

export interface ChatMessage {
  id: string
  sender: "user" | "ai"
  content: string
  timestamp: string
  mode?: string
  sources?: ChatSource[]
  error?: boolean
}

export interface AnalysisResult {
  jobId: string
  documents: DocumentResult[]
}

export interface Document {
  id: string
  fileName: string
  uploadedAt: string
  fileSize: number
  status: "processing" | "completed" | "failed"
}

export interface DocumentHistory {
  id: string
  userId: string
  documents: Document[]
}

export interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (data: {
    email: string
    username: string
    password: string
    rbacLevel: "admin" | "manager" | "analyst"
    managerId?: number
  }) => Promise<void>
  logout: () => Promise<void>
  documents: Document[]
  addDocument: (document: Document) => void
}
