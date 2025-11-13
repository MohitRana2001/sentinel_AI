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
  case_name?: string // NEW: Case name for grouping
}

// Job status response with per-artifact details
export interface JobStatusResponse {
  job_id: string
  status: ProcessingStatus
  case_name?: string
  parent_job_id?: string
  total_files: number
  processed_files: number
  progress_percentage: number
  current_stage?: string
  processing_stages?: Record<string, number>
  artifacts: ArtifactStatus[] // NEW: Per-artifact status
  started_at?: string
  completed_at?: string
  error_message?: string
}

// Per-artifact status tracking
export interface ArtifactStatus {
  id: number
  filename: string
  file_type: string
  status: ProcessingStatus
  current_stage?: string
  processing_stages?: Record<string, number>
  started_at?: string
  completed_at?: string
  error_message?: string
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

export type MediaType = 'document' | 'audio' | 'video' | 'cdr';

export type ProcessingStatus = 'queued' | 'processing' | 'completed' | 'failed';

// CDR (Call Data Record) specific types
export interface CDRFile extends MediaItem {
  mediaType: 'cdr'
  recordCount?: number
  dateRange?: {
    from: string
    to: string
  }
}

// Suspect Management types
export interface SuspectField {
  id: string
  key: string
  value: string
}

export interface Suspect {
  id?: number
  name: string
  phone_number: string
  photograph_base64: string
  details: Record<string, any>
  created_at?: string
  updated_at?: string
  // Legacy fields for backward compatibility
  fields?: SuspectField[]
  createdAt?: string
  updatedAt?: string
}

export interface SuspectDatabase {
  suspects: Suspect[]
}

export interface MediaItem {
  id: string
  fileName: string
  mediaType: MediaType
  uploadedAt: string
  fileSize: number
  status: ProcessingStatus
  jobId?: string
  summary?: string
  language?: string // Source language
  translatedLanguage?: string // Target language (usually 'en')
  progress?: number // 0-100
  transcription?: string
  duration?: number // For audio/video in seconds
  thumbnailUrl?: string // For video
  currentStage?: string // Current processing stage
  processingStages?: Record<string, number> // Stage timing data (in seconds)
  startedAt?: string // ISO timestamp
  completedAt?: string // ISO timestamp
  errorMessage?: string // Error message if failed
}

export interface Document extends MediaItem {
  mediaType: 'document'
}

export interface AudioFile extends MediaItem {
  mediaType: 'audio'
  duration?: number
  transcription?: string
}

export interface VideoFile extends MediaItem {
  mediaType: 'video'
  duration?: number
  transcription?: string
  thumbnailUrl?: string
}

export interface DocumentHistory {
  id: string
  userId: string
  documents: Document[]
}

// Upload Job - Can contain multiple media types
export interface UploadJob {
  files: FileWithMetadata[]
  suspects: Suspect[]
}

export interface FileWithMetadata {
  file: File
  mediaType: MediaType
  language?: string // For audio/video
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
  mediaItems: MediaItem[]
  addDocument: (document: Document) => void
  uploadMedia: (file: File, mediaType: MediaType, language?: string) => Promise<void>
  uploadJob: (job: UploadJob, caseName?: string, parentJobId?: string) => Promise<void> // UPDATED: Added caseName and parentJobId
}
