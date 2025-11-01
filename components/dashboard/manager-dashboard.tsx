"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api-client";
import {
  Users,
  UserPlus,
  Trash2,
  FileText,
  MessageSquare,
  Network,
} from "lucide-react";
import type { JobWithAnalyst } from "@/types";
import { useRouter } from "next/navigation";

interface CreateAnalystForm {
  email: string;
  username: string;
  password: string;
}

type TabType = "analysts" | "jobs";

export function ManagerDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>("jobs");

  // Analysts state
  const [analysts, setAnalysts] = useState<any[]>([]);
  const [loadingAnalysts, setLoadingAnalysts] = useState(false);

  // Jobs state
  const [jobs, setJobs] = useState<JobWithAnalyst[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);

  // Modal states
  const [showCreateAnalystModal, setShowCreateAnalystModal] = useState(false);
  const [analystForm, setAnalystForm] = useState<CreateAnalystForm>({
    email: "",
    username: "",
    password: "",
  });

  const [formLoading, setFormLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (activeTab === "analysts") {
      loadAnalysts();
    } else {
      loadJobs();
    }
  }, [activeTab]);

  const loadAnalysts = async () => {
    try {
      setLoadingAnalysts(true);
      const data = await apiClient.managerListAnalysts();
      setAnalysts(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analysts");
    } finally {
      setLoadingAnalysts(false);
    }
  };

  const loadJobs = async () => {
    try {
      setLoadingJobs(true);
      const data = await apiClient.getManagerJobs(15, 0);
      setJobs(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleCreateAnalyst = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setError("");

    try {
      await apiClient.managerCreateAnalyst(analystForm);
      setShowCreateAnalystModal(false);
      setAnalystForm({ email: "", username: "", password: "" });
      await loadAnalysts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create analyst");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteAnalyst = async (
    analystId: number,
    analystName: string
  ) => {
    if (!confirm(`Are you sure you want to delete analyst "${analystName}"?`)) {
      return;
    }

    try {
      await apiClient.managerDeleteAnalyst(analystId);
      await loadAnalysts();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete analyst");
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "bg-green-100 text-green-700";
      case "processing":
        return "bg-blue-100 text-blue-700";
      case "failed":
        return "bg-red-100 text-red-700";
      default:
        return "bg-yellow-100 text-yellow-700";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Manager Dashboard</h1>
          <p className="text-muted-foreground">
            Manage your analysts and view their jobs
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b">
          <button
            onClick={() => setActiveTab("jobs")}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === "jobs"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Jobs
          </button>
          <button
            onClick={() => setActiveTab("analysts")}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === "analysts"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Analysts
          </button>
        </div>

        {/* Analysts Tab */}
        {activeTab === "analysts" && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold">Your Analysts</h2>
              <Button onClick={() => setShowCreateAnalystModal(true)}>
                <UserPlus className="mr-2 h-4 w-4" />
                Create Analyst
              </Button>
            </div>

            {loadingAnalysts ? (
              <div className="text-center py-12">Loading analysts...</div>
            ) : analysts.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    No analysts created yet
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {analysts.map((analyst) => (
                  <Card key={analyst.id}>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">
                            {analyst.username}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            {analyst.email}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Created: {formatDate(analyst.created_at)}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            handleDeleteAnalyst(analyst.id, analyst.username)
                          }
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Jobs Tab */}
        {activeTab === "jobs" && (
          <div>
            <h2 className="text-2xl font-semibold mb-6">
              All Jobs from Your Analysts
            </h2>

            {loadingJobs ? (
              <div className="text-center py-12">Loading jobs...</div>
            ) : jobs.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No jobs found</p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 border-b">
                        <tr>
                          <th className="text-left p-4 font-medium">Job ID</th>
                          <th className="text-left p-4 font-medium">Analyst</th>
                          <th className="text-left p-4 font-medium">Status</th>
                          <th className="text-left p-4 font-medium">Files</th>
                          <th className="text-left p-4 font-medium">
                            Progress
                          </th>
                          <th className="text-left p-4 font-medium">Created</th>
                          <th className="text-left p-4 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map((job) => (
                          <tr
                            key={job.job_id}
                            className="border-b hover:bg-slate-50"
                          >
                            <td className="p-4">
                              <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                                {job.job_id.split("/")[2].substring(0, 8)}...
                              </code>
                            </td>
                            <td className="p-4">
                              <div>
                                <div className="font-medium text-sm">
                                  {job.analyst_username}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {job.analyst_email}
                                </div>
                              </div>
                            </td>
                            <td className="p-4">
                              <span
                                className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                                  job.status
                                )}`}
                              >
                                {job.status}
                              </span>
                            </td>
                            <td className="p-4 text-sm">
                              {job.processed_files}/{job.total_files}
                            </td>
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-600 transition-all"
                                    style={{
                                      width: `${job.progress_percentage}%`,
                                    }}
                                  />
                                </div>
                                <span className="text-xs text-muted-foreground">
                                  {Math.round(job.progress_percentage)}%
                                </span>
                              </div>
                            </td>
                            <td className="p-4 text-sm text-muted-foreground">
                              {formatDate(job.created_at)}
                            </td>
                            <td className="p-4">
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() =>
                                    router.push(`/results?jobId=${job.job_id}`)
                                  }
                                  title="View Summary"
                                >
                                  <FileText className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() =>
                                    router.push(`/graph?jobId=${job.job_id}`)
                                  }
                                  title="View Graph"
                                >
                                  <Network className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() =>
                                    router.push(`/chat?jobId=${job.job_id}`)
                                  }
                                  title="Chat"
                                >
                                  <MessageSquare className="h-4 w-4" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Create Analyst Modal */}
      {showCreateAnalystModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Create Analyst</CardTitle>
              <CardDescription>
                Add a new analyst under your management
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateAnalyst} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input
                    type="email"
                    value={analystForm.email}
                    onChange={(e) =>
                      setAnalystForm({ ...analystForm, email: e.target.value })
                    }
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    value={analystForm.username}
                    onChange={(e) =>
                      setAnalystForm({
                        ...analystForm,
                        username: e.target.value,
                      })
                    }
                    required
                    disabled={formLoading}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    value={analystForm.password}
                    onChange={(e) =>
                      setAnalystForm({
                        ...analystForm,
                        password: e.target.value,
                      })
                    }
                    required
                    disabled={formLoading}
                  />
                </div>
                {error && <div className="text-sm text-red-600">{error}</div>}
                <div className="flex gap-2">
                  <Button type="submit" disabled={formLoading}>
                    {formLoading ? "Creating..." : "Create Analyst"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowCreateAnalystModal(false);
                      setError("");
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
  );
}
