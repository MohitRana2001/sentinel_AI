"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { apiClient } from "@/lib/api-client"
import { Users, UserPlus, Trash2, Edit, ChevronDown, ChevronRight } from "lucide-react"
import type { Manager, Analyst } from "@/types"

interface CreateManagerForm {
  email: string
  username: string
  password: string
}

interface CreateAnalystForm {
  email: string
  username: string
  password: string
  manager_id: number
}

export function AdminDashboard() {
  const [managers, setManagers] = useState<Manager[]>([])
  const [expandedManagers, setExpandedManagers] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>("")
  
  // Modal states
  const [showManagerModal, setShowManagerModal] = useState(false)
  const [showAnalystModal, setShowAnalystModal] = useState(false)
  const [showReassignModal, setShowReassignModal] = useState(false)
  
  // Form states
  const [managerForm, setManagerForm] = useState<CreateManagerForm>({
    email: "",
    username: "",
    password: "",
  })
  const [analystForm, setAnalystForm] = useState<CreateAnalystForm>({
    email: "",
    username: "",
    password: "",
    manager_id: 0,
  })
  const [reassignData, setReassignData] = useState<{
    analystId: number
    analystName: string
    currentManagerId: number
    newManagerId: number
  } | null>(null)
  
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string>("")

  useEffect(() => {
    loadManagers()
  }, [])

  const loadManagers = async () => {
    try {
      setLoading(true)
      const data = await apiClient.listManagers()
      setManagers(data)
      setError("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load managers")
    } finally {
      setLoading(false)
    }
  }

  const toggleManager = (managerId: number) => {
    const newExpanded = new Set(expandedManagers)
    if (newExpanded.has(managerId)) {
      newExpanded.delete(managerId)
    } else {
      newExpanded.add(managerId)
    }
    setExpandedManagers(newExpanded)
  }

  const handleCreateManager = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError("")

    try {
      await apiClient.createManager(managerForm)
      setShowManagerModal(false)
      setManagerForm({ email: "", username: "", password: "" })
      await loadManagers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create manager")
    } finally {
      setFormLoading(false)
    }
  }

  const handleCreateAnalyst = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError("")

    try {
      await apiClient.createAnalyst(analystForm)
      setShowAnalystModal(false)
      setAnalystForm({ email: "", username: "", password: "", manager_id: 0 })
      await loadManagers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create analyst")
    } finally {
      setFormLoading(false)
    }
  }

  const handleDeleteManager = async (managerId: number, managerName: string) => {
    if (!confirm(`Are you sure you want to delete manager "${managerName}"?`)) {
      return
    }

    try {
      await apiClient.deleteManager(managerId)
      await loadManagers()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete manager")
    }
  }

  const handleDeleteAnalyst = async (analystId: number, analystName: string) => {
    if (!confirm(`Are you sure you want to delete analyst "${analystName}"?`)) {
      return
    }

    try {
      await apiClient.deleteAnalyst(analystId)
      await loadManagers()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete analyst")
    }
  }

  const handleReassignAnalyst = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reassignData) return

    setFormLoading(true)
    setFormError("")

    try {
      await apiClient.reassignAnalyst(reassignData.analystId, reassignData.newManagerId)
      setShowReassignModal(false)
      setReassignData(null)
      await loadManagers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to reassign analyst")
    } finally {
      setFormLoading(false)
    }
  }

  const openReassignModal = (analyst: Analyst, currentManagerId: number) => {
    setReassignData({
      analystId: analyst.id,
      analystName: analyst.username,
      currentManagerId,
      newManagerId: currentManagerId,
    })
    setShowReassignModal(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage managers and analysts</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="flex gap-4 mb-6">
          <Button onClick={() => setShowManagerModal(true)}>
            <UserPlus className="mr-2 h-4 w-4" />
            Create Manager
          </Button>
          <Button onClick={() => setShowAnalystModal(true)} variant="outline">
            <UserPlus className="mr-2 h-4 w-4" />
            Create Analyst
          </Button>
        </div>

        <div className="space-y-4">
          {managers.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No managers created yet</p>
              </CardContent>
            </Card>
          ) : (
            managers.map((manager) => (
              <Card key={manager.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => toggleManager(manager.id)}
                      className="flex items-center gap-2 flex-1 text-left hover:opacity-70 transition-opacity"
                    >
                      {expandedManagers.has(manager.id) ? (
                        <ChevronDown className="h-5 w-5" />
                      ) : (
                        <ChevronRight className="h-5 w-5" />
                      )}
                      <div>
                        <CardTitle className="text-xl">{manager.username}</CardTitle>
                        <CardDescription>{manager.email}</CardDescription>
                      </div>
                    </button>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {manager.analysts.length} analyst{manager.analysts.length !== 1 ? "s" : ""}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteManager(manager.id, manager.username)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {expandedManagers.has(manager.id) && (
                  <CardContent>
                    {manager.analysts.length === 0 ? (
                      <div className="p-4 text-center text-muted-foreground">
                        No analysts assigned to this manager
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {manager.analysts.map((analyst) => (
                          <div
                            key={analyst.id}
                            className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                          >
                            <div>
                              <div className="font-medium">{analyst.username}</div>
                              <div className="text-sm text-muted-foreground">{analyst.email}</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openReassignModal(analyst, manager.id)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteAnalyst(analyst.id, analyst.username)}
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Create Manager Modal */}
      {showManagerModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Create Manager</CardTitle>
              <CardDescription>Add a new manager to the system</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateManager} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input
                    type="email"
                    value={managerForm.email}
                    onChange={(e) => setManagerForm({ ...managerForm, email: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    value={managerForm.username}
                    onChange={(e) => setManagerForm({ ...managerForm, username: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    value={managerForm.password}
                    onChange={(e) => setManagerForm({ ...managerForm, password: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                {formError && <div className="text-sm text-red-600">{formError}</div>}
                <div className="flex gap-2">
                  <Button type="submit" disabled={formLoading}>
                    {formLoading ? "Creating..." : "Create Manager"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowManagerModal(false)
                      setFormError("")
                    }}
                    disabled={formLoading}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Create Analyst Modal */}
      {showAnalystModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Create Analyst</CardTitle>
              <CardDescription>Add a new analyst and assign to a manager</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateAnalyst} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input
                    type="email"
                    value={analystForm.email}
                    onChange={(e) => setAnalystForm({ ...analystForm, email: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    value={analystForm.username}
                    onChange={(e) => setAnalystForm({ ...analystForm, username: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    value={analystForm.password}
                    onChange={(e) => setAnalystForm({ ...analystForm, password: e.target.value })}
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Assign to Manager</label>
                  <select
                    value={analystForm.manager_id}
                    onChange={(e) =>
                      setAnalystForm({ ...analystForm, manager_id: Number(e.target.value) })
                    }
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    required
                    disabled={formLoading}
                  >
                    <option value="">Select a manager</option>
                    {managers.map((manager) => (
                      <option key={manager.id} value={manager.id}>
                        {manager.username} ({manager.email})
                      </option>
                    ))}
                  </select>
                </div>
                {formError && <div className="text-sm text-red-600">{formError}</div>}
                <div className="flex gap-2">
                  <Button type="submit" disabled={formLoading}>
                    {formLoading ? "Creating..." : "Create Analyst"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowAnalystModal(false)
                      setFormError("")
                    }}
                    disabled={formLoading}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Reassign Analyst Modal */}
      {showReassignModal && reassignData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Reassign Analyst</CardTitle>
              <CardDescription>
                Reassign {reassignData.analystName} to a different manager
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleReassignAnalyst} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">New Manager</label>
                  <select
                    value={reassignData.newManagerId}
                    onChange={(e) =>
                      setReassignData({ ...reassignData, newManagerId: Number(e.target.value) })
                    }
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    required
                    disabled={formLoading}
                  >
                    {managers.map((manager) => (
                      <option key={manager.id} value={manager.id}>
                        {manager.username} ({manager.email})
                      </option>
                    ))}
                  </select>
                </div>
                {formError && <div className="text-sm text-red-600">{formError}</div>}
                <div className="flex gap-2">
                  <Button type="submit" disabled={formLoading}>
                    {formLoading ? "Reassigning..." : "Reassign"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowReassignModal(false)
                      setReassignData(null)
                      setFormError("")
                    }}
                    disabled={formLoading}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

