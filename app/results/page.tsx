"use client";
import { useAuth } from "@/context/auth-context";
import { Header } from "@/components/common/header";
import { ResultsContainer } from "@/components/results/results-container";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { AnalysisResult, DocumentResult } from "@/types";
import { FolderOpen, ExternalLink } from "lucide-react";
import Link from "next/link";

export default function ResultsPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");

  const [jobResults, setJobResults] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobInfo, setJobInfo] = useState<any>(null);
  const [caseJobs, setCaseJobs] = useState<any[]>([]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/");
      return;
    }

    if (!jobId) {
      router.push("/dashboard");
      return;
    }

    loadJobResults();
  }, [isAuthenticated, jobId, router]);

  const loadJobResults = async () => {
    if (!jobId) return;

    try {
      setLoading(true);
      
      // Load job info first to get case name
      const jobStatus = await apiClient.getJobStatus(jobId);
      setJobInfo(jobStatus);
      
      // If job has a case name, load other jobs in the same case
      if (jobStatus.case_name) {
        try {
          const caseData = await apiClient.getCaseJobs(jobStatus.case_name);
          setCaseJobs(caseData.jobs || []);
        } catch (err) {
          console.error("Failed to load case jobs:", err);
        }
      }
      
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
    } catch (error) {
      console.error("Failed to fetch results:", error);
      setError(
        error instanceof Error ? error.message : "Failed to fetch results"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    router.push("/dashboard");
  };

  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <>
        <Header />
        <div className="min-h-screen flex items-center justify-center">
          <p>Loading results...</p>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Header />
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Header />
      <div className="container mx-auto p-6 space-y-6">
        {/* Case Context Card */}
        {jobInfo?.case_name && (
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-blue-600" />
                Case: {jobInfo.case_name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  <span className="text-gray-600">Total uploads in case:</span>
                  <span className="ml-2 font-semibold">{caseJobs.length || 0}</span>
                </div>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/cases/${encodeURIComponent(jobInfo.case_name)}`}>
                    View All Case Files
                    <ExternalLink className="ml-2 h-3 w-3" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {jobResults && (
          <ResultsContainer
            result={jobResults}
            onReset={handleReset}
            jobId={jobResults.jobId}
          />
        )}
      </div>
    </>
  );
}
