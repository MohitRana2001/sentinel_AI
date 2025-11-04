"use client";

import { useState, useEffect } from "react";
import { FileUpload } from "./file-upload";
import { ProcessingLoader } from "@/components/processing/processing-loader";
import { ResultsContainer } from "@/components/results/results-container";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import type { AnalysisResult, DocumentResult } from "@/types";
import { AdminDashboard } from "./admin-dashboard";
import { ManagerDashboard } from "./manager-dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Clock } from "lucide-react";

type AppState = "upload" | "processing" | "results";

export function DashboardPage() {
  const { user, addDocument } = useAuth();
  const [appState, setAppState] = useState<AppState>("upload");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [jobResults, setJobResults] = useState<AnalysisResult | null>(null);
  const [pastJobs, setPastJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [showPastJobs, setShowPastJobs] = useState(false);

  // Route based on user role
  if (user?.rbacLevel === "admin") {
    return <AdminDashboard />;
  }

  if (user?.rbacLevel === "manager") {
    return <ManagerDashboard />;
  }

  // Analyst dashboard continues below
  useEffect(() => {
    if (user?.rbacLevel === "analyst") {
      loadPastJobs();
    }
  }, [user?.rbacLevel]);

  const handleFilesSelected = async (files: File[]) => {
    if (files.length === 0) return;

    setUploadError(null);
    setAppState("processing");

    try {
      const response = await apiClient.uploadDocuments(files);
      setCurrentJobId(response.job_id);

      files.forEach((file) => {
        addDocument({
          id: `${response.job_id}-${file.name}`,
          fileName: file.name,
          uploadedAt: new Date().toISOString(),
          fileSize: Number.parseFloat((file.size / (1024 * 1024)).toFixed(2)),
          status: "processing",
        });
      });
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadError(error instanceof Error ? error.message : "Upload failed");
      setAppState("upload");
    }
  };

  const handleProcessingComplete = async (jobId: string) => {
    try {
      const results = await apiClient.getJobResults(jobId);

      if (results.documents.length === 0) {
        throw new Error("No processed documents were returned for this job.");
      }

      const documents: DocumentResult[] = [];

      for (const doc of results.documents) {
        let summary = doc.summary || "";
        let transcription = "";
        let translation = "";

        try {
          const summaryData = await apiClient.getDocumentSummary(doc.id);
          summary = summaryData.content;
        } catch (err) {
          console.info(`Summary unavailable for document ${doc.id}:`, err);
        }

        try {
          const transcriptionData = await apiClient.getDocumentTranscription(
            doc.id
          );
          transcription = transcriptionData.content;
        } catch (err) {
          console.info(
            `Transcription unavailable for document ${doc.id}:`,
            err
          );
        }

        try {
          const translationData = await apiClient.getDocumentTranslation(
            doc.id
          );
          translation = translationData.content;
        } catch (err) {
          console.info(`Translation unavailable for document ${doc.id}:`, err);
        }

        documents.push({
          id: doc.id,
          fileName: doc.filename,
          uploadedAt: doc.created_at,
          fileType: doc.file_type,
          summary,
          transcription,
          translation,
          hasAudio: doc.file_type === "audio" || doc.file_type === "video",
          isNonEnglish: translation.length > 0,
        });
      }

      setJobResults({
        jobId,
        documents,
      });

      setAppState("results");
    } catch (error) {
      console.error("Failed to fetch results:", error);
      setUploadError(
        error instanceof Error ? error.message : "Failed to fetch results"
      );
      setAppState("upload");
    }
  };

  const handleReset = () => {
    setAppState("upload");
    setCurrentJobId(null);
    setJobResults(null);
    setUploadError(null);
  };

  const loadPastJobs = async () => {
    try {
      setLoadingJobs(true);
      const jobs = await apiClient.getAnalystJobs(15, 0);
      setPastJobs(jobs);
    } catch (err) {
      console.error("Failed to load past jobs:", err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const viewPastJob = async (jobId: string) => {
    try {
      setCurrentJobId(jobId);
      setAppState("processing");
      // Simulate loading and then show results
      setTimeout(async () => {
        await handleProcessingComplete(jobId);
      }, 100);
    } catch (err) {
      console.error("Failed to load job:", err);
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
    <div className="min-h-[calc(100vh-64px)] bg-gradient-to-br from-slate-50 via-blue-50/40 to-indigo-50/40">
      {appState === "upload" && (
        <div className="max-w-6xl mx-auto pt-16 px-4 pb-24">
          <div className="mb-10 text-center">
            <h1 className="text-5xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Document Intelligence
            </h1>
            <p className="text-lg text-slate-600">
              Upload documents to generate summaries, graphs, and chat-ready
              knowledge.
            </p>
          </div>

          <div className="max-w-2xl mx-auto mb-8">
            {uploadError && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                {uploadError}
              </div>
            )}
            <FileUpload onFilesSelected={handleFilesSelected} />
          </div>

          {/* Past Jobs Section */}
          <div className="mt-12">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Your Past Jobs</h2>
              <Button variant="outline" onClick={() => loadPastJobs()}>
                <Clock className="mr-2 h-4 w-4" />
                Refresh Jobs
              </Button>
            </div>

            {
              <div>
                {loadingJobs ? (
                  <Card>
                    <CardContent className="p-12 text-center">
                      <p className="text-muted-foreground">Loading jobs...</p>
                    </CardContent>
                  </Card>
                ) : pastJobs.length === 0 ? (
                  <Card>
                    <CardContent className="p-12 text-center">
                      <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-muted-foreground">
                        No past jobs found
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid gap-4">
                    {pastJobs.map((job) => (
                      <Card
                        key={job.job_id}
                        className="hover:shadow-lg transition-shadow"
                      >
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                                  {job.job_id}
                                </code>
                                <span
                                  className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                                    job.status
                                  )}`}
                                >
                                  {job.status}
                                </span>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span>
                                  {job.processed_files}/{job.total_files} files
                                </span>
                                <span>
                                  {Math.round(job.progress_percentage)}%
                                  complete
                                </span>
                                <span>{formatDate(job.created_at)}</span>
                              </div>
                            </div>
                            {job.status === "completed" && (
                              <Button onClick={() => viewPastJob(job.job_id)}>
                                View Results
                              </Button>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            }
          </div>
        </div>
      )}

      {appState === "processing" && currentJobId && (
        <ProcessingLoader
          jobId={currentJobId}
          onComplete={handleProcessingComplete}
        />
      )}

      {appState === "results" && jobResults && (
        <ResultsContainer
          result={jobResults}
          onReset={handleReset}
          jobId={jobResults.jobId}
        />
      )}
    </div>
  );
}
