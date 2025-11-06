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

  async getJobGraph(jobId: string, documentIds?: number[]): Promise<GraphData> {
    let url = `${this.baseUrl}/jobs/${jobId}/graph`
    if (documentIds && documentIds.length > 0) {
      const params = new URLSearchParams()
      params.append("document_ids", documentIds.join(','))
      url += `?${params.toString()}`
    }

    const response = await fetch(url, {
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
    documentIds?: number[],
  ): Promise<ChatResponse> {
    const params = new URLSearchParams()
    params.append("message", message)
    if (jobId) params.append("job_id", jobId)
    if (documentIds && documentIds.length > 0) {
      params.append("document_ids", documentIds.join(','))
    }

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

  // ============ USER MANAGEMENT APIs ============

  /**
   * Admin: Sign up as the first admin user
   */
  async adminSignup(data: {
    email: string
    username: string
    password: string
    secret_key: string
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Admin signup failed" }))
      throw new Error(error.detail || "Admin signup failed")
    }

    return response.json()
  }

  /**
   * Admin: Create a new manager
   */
  async createManager(data: {
    email: string
    username: string
    password: string
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/managers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to create manager" }))
      throw new Error(error.detail || "Failed to create manager")
    }

    return response.json()
  }

  /**
   * Admin: List all managers with their analysts
   */
  async listManagers(): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/admin/managers`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to list managers")
    }

    return response.json()
  }

  /**
   * Admin: Delete a manager
   */
  async deleteManager(managerId: number): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/managers/${managerId}`, {
      method: "DELETE",
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to delete manager" }))
      throw new Error(error.detail || "Failed to delete manager")
    }

    return response.json()
  }

  /**
   * Admin: Create a new analyst
   */
  async createAnalyst(data: {
    email: string
    username: string
    password: string
    manager_id: number
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/analysts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to create analyst" }))
      throw new Error(error.detail || "Failed to create analyst")
    }

    return response.json()
  }

  /**
   * Admin: List all analysts
   */
  async listAnalysts(): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/admin/analysts`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to list analysts")
    }

    return response.json()
  }

  /**
   * Admin: Reassign an analyst to a different manager
   */
  async reassignAnalyst(analystId: number, newManagerId: number): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/analysts/${analystId}/manager`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify({ new_manager_id: newManagerId }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to reassign analyst" }))
      throw new Error(error.detail || "Failed to reassign analyst")
    }

    return response.json()
  }

  /**
   * Admin: Delete an analyst
   */
  async deleteAnalyst(analystId: number): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/analysts/${analystId}`, {
      method: "DELETE",
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to delete analyst" }))
      throw new Error(error.detail || "Failed to delete analyst")
    }

    return response.json()
  }

  /**
   * Manager: Create an analyst under themselves
   */
  async managerCreateAnalyst(data: {
    email: string
    username: string
    password: string
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/manager/analysts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to create analyst" }))
      throw new Error(error.detail || "Failed to create analyst")
    }

    return response.json()
  }

  /**
   * Manager: List their analysts
   */
  async managerListAnalysts(): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/manager/analysts`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to list analysts")
    }

    return response.json()
  }

  /**
   * Manager: Delete one of their analysts
   */
  async managerDeleteAnalyst(analystId: number): Promise<any> {
    const response = await fetch(`${this.baseUrl}/manager/analysts/${analystId}`, {
      method: "DELETE",
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to delete analyst" }))
      throw new Error(error.detail || "Failed to delete analyst")
    }

    return response.json()
  }

  /**
   * Manager: Get all jobs from their analysts
   */
  async getManagerJobs(limit: number = 50, offset: number = 0): Promise<{
    jobs: any[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const response = await fetch(
      `${this.baseUrl}/manager/jobs?limit=${limit}&offset=${offset}`,
      {
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error("Failed to fetch manager jobs")
    }

    return response.json()
  }

  /**
   * Analyst: Get own jobs
   */
  async getAnalystJobs(limit: number = 50, offset: number = 0): Promise<{
    jobs: any[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const response = await fetch(
      `${this.baseUrl}/analyst/jobs?limit=${limit}&offset=${offset}`,
      {
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error("Failed to fetch analyst jobs")
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
