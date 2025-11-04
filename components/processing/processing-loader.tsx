"use client";

import { useState, useEffect } from "react";
import {
  Loader2,
  CheckCircle2,
  FileText,
  Languages,
  BarChart3,
  Brain,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface ProcessingLoaderProps {
  jobId: string;
  onComplete: (jobId: string) => void;
}

type StepStatus = "pending" | "processing" | "completed";

interface ProcessingStep {
  id: number;
  label: string;
  icon: typeof FileText;
  status: StepStatus;
}

const PROCESSING_STEPS: ProcessingStep[] = [
  {
    id: 1,
    label: "Document Extraction",
    icon: FileText,
    status: "pending" as const,
  },
  { id: 2, label: "Translation", icon: Languages, status: "pending" as const },
  {
    id: 3,
    label: "Summarization",
    icon: BarChart3,
    status: "pending" as const,
  },
  { id: 4, label: "Knowledge Graph", icon: Brain, status: "pending" as const },
];

export function ProcessingLoader({ jobId, onComplete }: ProcessingLoaderProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState(PROCESSING_STEPS);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState(
    "Initializing processing..."
  );

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    const pollJobStatus = async () => {
      try {
        const status = await apiClient.getJobStatus(jobId);

        setProgress(status.progress_percentage);

        // Update status message
        if (status.status === "processing") {
          setStatusMessage(
            `Processing ${status.processed_files}/${status.total_files} files...`
          );
        } else if (status.status === "completed") {
          setStatusMessage("Processing complete!");
          clearInterval(pollInterval);
          setTimeout(() => {
            onComplete(jobId);
          }, 1000);
        } else if (status.status === "failed") {
          setStatusMessage(status.error_message || "Processing failed");
          clearInterval(pollInterval);
        } else {
          setStatusMessage("Queued for processing...");
        }

        // Update steps based on progress
        const stepIndex = Math.floor(
          (status.progress_percentage / 100) * PROCESSING_STEPS.length
        );
        setCurrentStep(stepIndex);
      } catch (error) {
        console.error("Failed to poll job status:", error);
        // Continue polling even if there's an error
      }
    };

    // Start polling immediately and then every 2 seconds
    pollJobStatus();
    pollInterval = setInterval(pollJobStatus, 2000);

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [jobId, onComplete]);

  useEffect(() => {
    const newSteps = PROCESSING_STEPS.map((step, index) => {
      if (index < currentStep) {
        return { ...step, status: "completed" as const };
      } else if (index === currentStep) {
        return { ...step, status: "processing" as const };
      }
      return { ...step, status: "pending" as const };
    });
    setSteps(newSteps);
  }, [currentStep]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 bg-white/95 backdrop-blur-sm shadow-2xl border-0">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full mb-4 shadow-lg">
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          </div>
          <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Processing Documents
          </h2>
          <p className="text-slate-600">{statusMessage}</p>
          <p className="text-xs text-slate-400 mt-1">
            Job ID: {jobId.slice(0, 8)}...
          </p>
        </div>

        <div className="space-y-4 mb-6">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.id}
                className={`flex items-center gap-4 p-3 rounded-lg transition-all ${
                  step.status === "processing"
                    ? "bg-blue-50 border border-blue-200"
                    : step.status === "completed"
                    ? "bg-green-50 border border-green-200"
                    : "bg-slate-50"
                }`}
              >
                {step.status === "completed" ? (
                  <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 animate-in zoom-in" />
                ) : step.status === "processing" ? (
                  <Loader2 className="w-6 h-6 text-blue-600 animate-spin flex-shrink-0" />
                ) : (
                  <Icon className="w-6 h-6 text-slate-400 flex-shrink-0" />
                )}
                <span
                  className={`font-medium ${
                    step.status === "completed"
                      ? "text-green-700"
                      : step.status === "processing"
                      ? "text-blue-700"
                      : "text-slate-500"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>

        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-slate-600 font-medium">Overall Progress</span>
            <span className="font-bold text-blue-600">
              {Math.round(progress)}%
            </span>
          </div>
          <div className="relative h-3 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-500 ease-out rounded-full"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-white/30 animate-pulse" />
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
