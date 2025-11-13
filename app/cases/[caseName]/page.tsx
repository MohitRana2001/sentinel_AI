"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/status-badge";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api-client";
import { Loader2, FileText, Users, Calendar, ArrowLeft, ExternalLink, FolderOpen } from "lucide-react";
import Link from "next/link";

interface Job {
  job_id: string;
  case_name: string;
  status: string;
  total_files: number;
  processed_files: number;
  progress_percentage: number;
  suspects_count: number;
  created_at: string;
  completed_at: string | null;
  parent_job_id: string | null;
}

interface CaseData {
  case_name: string;
  jobs: Job[];
  total_jobs: number;
  total_files: number;
  total_suspects: number;
}

export default function CasePage() {
  const params = useParams();
  const router = useRouter();
  const caseName = decodeURIComponent(params.caseName as string);
  
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCaseData();
  }, [caseName]);

  const loadCaseData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getCaseJobs(caseName);
      setCaseData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load case data");
      console.error("Failed to load case data:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-IN", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleViewResults = (jobId: string) => {
    router.push(`/results?jobId=${encodeURIComponent(jobId)}`);
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto animate-spin text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Loading case data...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <FolderOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to load case</h3>
            <p className="text-muted-foreground mb-4">{error || "Case not found"}</p>
            <Button variant="outline" onClick={() => router.push("/dashboard")}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <FolderOpen className="h-8 w-8 text-blue-500" />
              {caseName}
            </h1>
            <p className="text-muted-foreground">Case Overview & Timeline</p>
          </div>
        </div>
        <Button variant="outline">
          Export Case Report
        </Button>
      </div>

      {/* Case Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Total Uploads
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{caseData.total_jobs || caseData.jobs.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Total Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {caseData.jobs.reduce((sum, job) => sum + job.total_files, 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <Users className="h-4 w-4" />
              Total Suspects
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {caseData.jobs.reduce((sum, job) => sum + (job.suspects_count || 0), 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Completed Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {caseData.jobs.filter(job => job.status === 'completed').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Jobs Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Timeline</CardTitle>
          <CardDescription>
            All uploads and processing jobs for this case
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {caseData.jobs.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No jobs found for this case
              </p>
            ) : (
              caseData.jobs.map((job) => (
                <div
                  key={job.job_id}
                  className={`flex items-center gap-4 p-4 border rounded-lg hover:bg-slate-50 transition-colors ${
                    job.parent_job_id ? "ml-8 border-l-4 border-l-blue-300" : ""
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {job.parent_job_id && (
                        <span className="text-muted-foreground text-sm">↳</span>
                      )}
                      <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                        {job.job_id}
                      </code>
                      <StatusBadge status={job.status as any} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {job.processed_files}/{job.total_files} files
                      </span>
                      {job.suspects_count > 0 && (
                        <span className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {job.suspects_count} suspect(s)
                        </span>
                      )}
                      <span>{Math.round(job.progress_percentage)}% complete</span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(job.created_at)}
                      </span>
                    </div>
                  </div>
                  {job.status === "completed" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewResults(job.job_id)}
                    >
                      View Results
                      <ExternalLink className="ml-2 h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
