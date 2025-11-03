"use client";

import { useState } from "react";
import type { AnalysisResult } from "@/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChatTab } from "./chat-tab";
import { SummaryTab } from "./summary-tab";
import { TranscriptionTab } from "./transcription-tab";
import { TranslationTab } from "./translation-tab";
import { GraphVisualization } from "./graph-visualization";
import { ArrowLeft, Check } from "lucide-react";

interface ResultsContainerProps {
  result: AnalysisResult;
  onReset: () => void;
  jobId: string;
}

type TabType = "chat" | "summary" | "transcription" | "translation" | "graph";

export function ResultsContainer({
  result,
  onReset,
  jobId,
}: ResultsContainerProps) {
  const [activeTab, setActiveTab] = useState<TabType>("summary");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([
    result.documents[0]?.id ?? 0,
  ]);

  // Get selected documents for rendering
  const selectedDocuments = result.documents.filter((doc) =>
    selectedDocumentIds.includes(doc.id)
  );

  // Check if any selected document has audio or needs translation
  const hasAnyAudio = selectedDocuments.some((doc) => doc.hasAudio);
  const hasAnyTranslation = selectedDocuments.some((doc) => doc.isNonEnglish);

  const tabs: Array<{ id: TabType; label: string; visible: boolean }> = [
    { id: "summary", label: "Summary", visible: true },
    {
      id: "transcription",
      label: "Transcription",
      visible: hasAnyAudio && selectedDocumentIds.length === 1,
    },
    {
      id: "translation",
      label: "Translation",
      visible: hasAnyTranslation && selectedDocumentIds.length === 1,
    },
    { id: "graph", label: "Knowledge Graph", visible: true },
    { id: "chat", label: "Chat", visible: true },
  ];

  const visibleTabs = tabs.filter((tab) => tab.visible);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Analysis Results</h1>
            <p className="text-muted-foreground mt-1">
              {result.documents.length} document
              {result.documents.length === 1 ? "" : "s"} processed in Job{" "}
              {jobId.slice(0, 8)}…
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onReset}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
        </div>

        {/* Document selector */}
        <Card className="p-4 bg-white border border-slate-200">
          <p className="text-sm text-slate-600 mb-3">
            Click documents to select/unselect for viewing:
          </p>
          <div className="flex flex-wrap gap-3">
            {result.documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => {
                  setSelectedDocumentIds((prev) =>
                    prev.includes(doc.id)
                      ? prev.filter((id) => id !== doc.id)
                      : [...prev, doc.id]
                  );
                }}
                className={`px-4 py-2 rounded-lg border-2 transition-all ${
                  selectedDocumentIds.includes(doc.id)
                    ? "bg-blue-100 border-blue-500 shadow-md"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  {selectedDocumentIds.includes(doc.id) && (
                    <Check className="h-4 w-4 text-blue-600" />
                  )}
                  <span
                    className={
                      selectedDocumentIds.includes(doc.id)
                        ? "font-semibold"
                        : ""
                    }
                  >
                    {doc.fileName}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        {/* Tabs */}
        <Card className="mb-6">
          <div className="flex border-b overflow-x-auto">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 font-medium text-sm transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === "summary" && (
              <SummaryTab documents={selectedDocuments} />
            )}

            {activeTab === "transcription" && selectedDocuments[0] && (
              <TranscriptionTab
                transcription={selectedDocuments[0].transcription || ""}
              />
            )}

            {activeTab === "translation" && selectedDocuments[0] && (
              <TranslationTab
                translation={selectedDocuments[0].translation || ""}
              />
            )}

            {activeTab === "graph" && (
              <GraphVisualization
                jobId={jobId}
                selectedDocumentIds={selectedDocumentIds}
              />
            )}

            {activeTab === "chat" && (
              <ChatTab
                jobId={jobId}
                documents={result.documents}
                selectedDocumentIds={selectedDocumentIds}
              />
            )}
          </div>
        </Card>

        {/* Metadata */}
        <Card className="p-4 bg-muted/40 border border-slate-200">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-slate-500 uppercase text-xs tracking-wide">
                <tr>
                  <th className="pb-2 pr-4">File Name</th>
                  <th className="pb-2 pr-4">Uploaded</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Has Audio</th>
                  <th className="pb-2 pr-4">Needs Translation</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                {result.documents.map((doc) => (
                  <tr key={doc.id} className="border-t border-slate-200/70">
                    <td className="py-2 pr-4 font-medium">{doc.fileName}</td>
                    <td className="py-2 pr-4">
                      {new Date(doc.uploadedAt).toLocaleString("en-IN", {
                        timeZone: "Asia/Kolkata",
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-2 pr-4 capitalize">{doc.fileType}</td>
                    <td className="py-2 pr-4">{doc.hasAudio ? "Yes" : "No"}</td>
                    <td className="py-2 pr-4">
                      {doc.isNonEnglish ? "Yes" : "No"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
