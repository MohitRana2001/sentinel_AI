export type UserRole = "analyst" | "manager" | "admin" | "super_admin"

export interface User {
  id: string
  email: string
  role: UserRole
  name: string
}

export interface ChartData {
  name: string
  value: number
  category: string
}

export interface AnalysisResult {
  id: string
  fileName: string
  uploadedAt: string
  summary: string
  transcription: string | null
  translation: string | null
  hasAudio: boolean
  isNonEnglish: boolean
  chartData: ChartData[]
}

export interface ChatMessage {
  id: string
  sender: "user" | "ai"
  content: string
  timestamp: string
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
  login: (email: string, password: string) => boolean
  logout: () => void
  documents: Document[]
  addDocument: (document: Document) => void
}
