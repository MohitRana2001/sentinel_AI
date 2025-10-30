"use client";

import { useState } from "react";
import { FileUpload } from "./file-upload";
import { ProcessingLoader } from "@/components/processing/processing-loader";
import { ResultsContainer } from "@/components/results/results-container";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import type { AnalysisResult, DocumentResult } from "@/types";

type AppState = "upload" | "processing" | "results";

export function DashboardPage() {
  const [appState, setAppState] = useState<AppState>("upload");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [jobResults, setJobResults] = useState<AnalysisResult | null>(null);
  const { addDocument } = useAuth();

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
          console.info(`Transcription unavailable for document ${doc.id}:`, err);
        }

        try {
          const translationData = await apiClient.getDocumentTranslation(doc.id);
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

  return (
    <div className="min-h-[calc(100vh-64px)] bg-gradient-to-br from-slate-50 via-blue-50/40 to-indigo-50/40">
      {appState === "upload" && (
        <div className="max-w-2xl mx-auto pt-16 px-4 pb-24">
          <div className="mb-10 text-center">
            <h1 className="text-5xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Document Intelligence
            </h1>
            <p className="text-lg text-slate-600">
              Upload documents to generate summaries, graphs, and chat-ready
              knowledge.
            </p>
          </div>
          {uploadError && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {uploadError}
            </div>
          )}
          <FileUpload onFilesSelected={handleFilesSelected} />
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
