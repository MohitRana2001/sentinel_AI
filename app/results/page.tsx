"use client";
import { useAuth } from "@/context/auth-context";
import { Header } from "@/components/common/header";
import { ResultsContainer } from "@/components/results/results-container";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { AnalysisResult, DocumentResult } from "@/types";

export default function ResultsPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");

  const [jobResults, setJobResults] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      {jobResults && (
        <ResultsContainer
          result={jobResults}
          onReset={handleReset}
          jobId={jobResults.jobId}
        />
      )}
    </>
  );
}
