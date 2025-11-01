"use client";
import { useAuth } from "@/context/auth-context";
import { Header } from "@/components/common/header";
import { ChatTab } from "@/components/results/chat-tab";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { DocumentResult } from "@/types";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function ChatPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");

  const [documents, setDocuments] = useState<DocumentResult[]>([]);
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

    loadDocuments();
  }, [isAuthenticated, jobId, router]);

  const loadDocuments = async () => {
    if (!jobId) return;

    try {
      setLoading(true);
      const results = await apiClient.getJobResults(jobId);

      const docs: DocumentResult[] = results.documents.map((doc) => ({
        id: doc.id,
        fileName: doc.filename,
        uploadedAt: doc.created_at,
        fileType: doc.file_type,
        summary: doc.summary || "",
        transcription: "",
        translation: "",
        hasAudio: doc.file_type === "audio" || doc.file_type === "video",
        isNonEnglish: false,
      }));

      setDocuments(docs);
    } catch (error) {
      console.error("Failed to fetch documents:", error);
      setError(
        error instanceof Error ? error.message : "Failed to fetch documents"
      );
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <>
        <Header />
        <div className="min-h-screen flex items-center justify-center">
          <p>Loading chat...</p>
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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <div className="max-w-5xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Chat with Documents</h1>
              <p className="text-muted-foreground mt-1">
                Ask questions about documents in Job {jobId.slice(0, 8)}…
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/dashboard")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
          <ChatTab jobId={jobId} documents={documents} />
        </div>
      </div>
    </>
  );
}
