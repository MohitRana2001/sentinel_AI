export interface User {
  id: string
  email: string
  name: string
  rbacLevel: "station" | "district" | "state"
  stationId?: string | null
  districtId?: string | null
  stateId?: string | null
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
    rbacLevel: "station" | "district" | "state"
    stationId?: string
    districtId?: string
    stateId?: string
  }) => Promise<void>
  logout: () => Promise<void>
  documents: Document[]
  addDocument: (document: Document) => void
}
