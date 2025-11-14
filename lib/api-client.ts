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
  current_stage: string | null
  processing_stages: Record<string, number>
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  case_name?: string | null
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
  suspects: Array<{
    id: string
    fields: Array<{
      id: string
      key: string
      value: string
    }>
    created_at: string
    updated_at: string
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

// Person of Interest interfaces
interface PersonOfInterest {
  id?: number
  name: string
  phone_number: string
  photograph_base64: string
  details: Record<string, any>
  created_at?: string
  updated_at?: string
}

interface PersonOfInterestCreate {
  name: string
  phone_number: string
  photograph_base64: string
  details: Record<string, any>
}

interface PersonOfInterestUpdate {
  name?: string
  phone_number?: string
  photograph_base64?: string
  details?: Record<string, any>
}

interface PersonOfInterestImport {
  persons: PersonOfInterestCreate[]
}

interface PersonOfInterestListResponse {
  total: number
  persons: PersonOfInterest[]
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

  async uploadDocuments(
    files: File[], 
    options?: {
      mediaTypes?: string[]
      languages?: string[]
      suspects?: string
      caseName?: string
      parentJobId?: string
    }
  ): Promise<UploadResponse> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append("files", file)
    })
    
    // Add optional metadata
    if (options?.mediaTypes) {
      options.mediaTypes.forEach(type => formData.append("media_types", type))
    }
    if (options?.languages) {
      options.languages.forEach(lang => formData.append("languages", lang))
    }
    if (options?.suspects) {
      formData.append("suspects", options.suspects)
    }
    if (options?.caseName) {
      formData.append("case_name", options.caseName)
    }
    if (options?.parentJobId) {
      formData.append("parent_job_id", options.parentJobId)
    }

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
  
  async getCases(): Promise<{ cases: string[] }> {
    const response = await fetch(`${this.baseUrl}/cases`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch cases")
    }

    return response.json()
  }
  
  async getCaseJobs(caseName: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/cases/${encodeURIComponent(caseName)}/jobs`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch case jobs")
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
    const encodedJobId = encodeURIComponent(jobId);
    const response = await fetch(`${this.baseUrl}/jobs/${encodedJobId}/results`, {
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
  async getManagerJobs(limit: number = 50, offset: number = 0): Promise<any[]> {
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
  async getAnalystJobs(limit: number = 50, offset: number = 0): Promise<any[]> {
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

  // ==========================================
  // Person of Interest API Methods
  // ==========================================

  /**
   * Create a new Person of Interest
   */
  async createPOI(poi: PersonOfInterestCreate): Promise<{ id: number; name: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/person-of-interest`, {
      method: "POST",
      headers: {
        ...this.getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(poi),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to create Person of Interest")
    }

    return response.json()
  }

  /**
   * Import multiple Persons of Interest
   */
  async importPOIs(import_data: PersonOfInterestImport): Promise<{
    success: number
    created: string[]
    errors: string[]
    message: string
  }> {
    const response = await fetch(`${this.baseUrl}/person-of-interest/import`, {
      method: "POST",
      headers: {
        ...this.getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(import_data),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to import Persons of Interest")
    }

    return response.json()
  }

  /**
   * Get all Persons of Interest
   */
  async getPOIs(skip: number = 0, limit: number = 100): Promise<PersonOfInterestListResponse> {
    const response = await fetch(
      `${this.baseUrl}/person-of-interest?skip=${skip}&limit=${limit}`,
      {
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error("Failed to fetch Persons of Interest")
    }

    return response.json()
  }

  /**
   * Get a specific Person of Interest by ID
   */
  async getPOI(poiId: number): Promise<PersonOfInterest> {
    const response = await fetch(`${this.baseUrl}/person-of-interest/${poiId}`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Person of Interest not found")
    }

    return response.json()
  }

  /**
   * Update a Person of Interest
   */
  async updatePOI(poiId: number, updates: PersonOfInterestUpdate): Promise<{ id: number; name: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/person-of-interest/${poiId}`, {
      method: "PUT",
      headers: {
        ...this.getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to update Person of Interest")
    }

    return response.json()
  }

  /**
   * Delete a Person of Interest
   */
  async deletePOI(poiId: number): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/person-of-interest/${poiId}`, {
      method: "DELETE",
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to delete Person of Interest")
    }

    return response.json()
  }

  // POI namespace for organized access
  poi = {
    create: async (poi: PersonOfInterestCreate): Promise<{ id: number; name: string; message: string }> => {
      return this.createPOI(poi)
    },
    getAll: async (skip: number = 0, limit: number = 100): Promise<PersonOfInterest[]> => {
      const response = await this.getPOIs(skip, limit)
      return response.persons
    },
    getById: async (poiId: number): Promise<PersonOfInterest> => {
      return this.getPOI(poiId)
    },
    update: async (poiId: number, updates: PersonOfInterestUpdate): Promise<{ id: number; name: string; message: string }> => {
      return this.updatePOI(poiId, updates)
    },
    delete: async (poiId: number): Promise<{ message: string }> => {
      return this.deletePOI(poiId)
    },
    importBulk: async (persons: PersonOfInterestCreate[]): Promise<{
      success: number
      created: string[]
      errors: string[]
      message: string
    }> => {
      return this.importPOIs({ persons })
    }
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
  PersonOfInterest,
  PersonOfInterestCreate,
  PersonOfInterestUpdate,
  PersonOfInterestImport,
  PersonOfInterestListResponse,
}
