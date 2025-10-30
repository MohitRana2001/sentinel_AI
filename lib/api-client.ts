const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

interface UploadResponse {
  job_id: string
  status: string
  total_files: number
  message: string
}

interface JobStatus {
  job_id: string
  status: string
  total_files: number
  processed_files: number
  progress_percentage: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

interface JobResults {
  job_id: string
  status: string
  completed_at: string | null
  documents: Array<{
    id: number
    filename: string
    file_type: string
    summary: string | null
    created_at: string
  }>
}

interface DocumentContent {
  document_id: number
  filename: string
  content: string
  content_type: string
}

interface GraphData {
  nodes: Array<{
    id: string
    label: string
    type: string
    properties: Record<string, any>
  }>
  relationships: Array<{
    source: string
    target: string
    type: string
    properties: Record<string, any>
  }>
}

interface ChatResponse {
  response: string
  mode: string
  sources: Array<{
    document_id: number
    chunk_index: number
    chunk_text: string
    metadata: Record<string, any>
  }>
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private getAuthToken(): string | null {
    if (typeof window === "undefined") return null
    return window.localStorage.getItem("sentinel-auth-token")
  }

  private getAuthHeaders(): HeadersInit {
    const token = this.getAuthToken()
    if (token) {
      return {
        Authorization: `Bearer ${token}`,
      }
    }
    return {}
  }

  async uploadDocuments(files: File[]): Promise<UploadResponse> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append("files", file)
    })

    const response = await fetch(`${this.baseUrl}/upload`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }))
      throw new Error(error.detail || "Upload failed")
    }

    return response.json()
  }

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/status`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch job status")
    }

    return response.json()
  }

  async getJobResults(jobId: string): Promise<JobResults> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/results`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch job results")
    }

    return response.json()
  }

  async getJobs(limit: number = 10, offset: number = 0): Promise<Array<any>> {
    const response = await fetch(`${this.baseUrl}/jobs?limit=${limit}&offset=${offset}`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch jobs")
    }

    return response.json()
  }

  async getDocumentSummary(documentId: number): Promise<DocumentContent> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/summary`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch summary")
    }

    return response.json()
  }

  async getDocumentTranscription(documentId: number): Promise<DocumentContent> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/transcription`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch transcription")
    }

    return response.json()
  }

  async getDocumentTranslation(documentId: number): Promise<DocumentContent> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/translation`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch translation")
    }

    return response.json()
  }

  async getJobGraph(jobId: string): Promise<GraphData> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/graph`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch graph")
    }

    return response.json()
  }

  async chat(
    message: string,
    jobId?: string,
    documentId?: number,
  ): Promise<ChatResponse> {
    const params = new URLSearchParams()
    params.append("message", message)
    if (jobId) params.append("job_id", jobId)
    if (documentId) params.append("document_id", documentId.toString())

    const url = `${this.baseUrl}/chat?${params.toString()}`

    const response = await fetch(url, {
      method: "POST",
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Chat request failed")
    }

    return response.json()
  }

  /**
   * Get API configuration
   */
  async getConfig(): Promise<{
    max_upload_files: number
    max_file_size_mb: number
    allowed_extensions: string[]
    rbac_levels: string[]
  }> {
    const response = await fetch(`${this.baseUrl}/config`)

    if (!response.ok) {
      throw new Error("Failed to fetch config")
    }

    return response.json()
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{
    status: string
    upload_limits: {
      max_files: number
      max_size_mb: number
    }
  }> {
    const response = await fetch(`${this.baseUrl}/health`)

    if (!response.ok) {
      throw new Error("Health check failed")
    }

    return response.json()
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export types
export type {
  UploadResponse,
  JobStatus,
  JobResults,
  DocumentContent,
  GraphData,
  ChatResponse,
}
