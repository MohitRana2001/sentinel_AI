"use client"

import { useState } from "react"
import type { AnalysisResult } from "@/types"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ChatTab } from "./chat-tab"
import { SummaryTab } from "./summary-tab"
import { TranscriptionTab } from "./transcription-tab"
import { TranslationTab } from "./translation-tab"
import { VisualizationTab } from "./visualization-tab"
import { ArrowLeft, Download } from "lucide-react"

interface ResultsContainerProps {
  result: AnalysisResult
  onReset: () => void
}

type TabType = "chat" | "summary" | "transcription" | "translation" | "visualization"

export function ResultsContainer({ result, onReset }: ResultsContainerProps) {
  const [activeTab, setActiveTab] = useState<TabType>("chat")

  const tabs: Array<{ id: TabType; label: string; visible: boolean }> = [
    { id: "chat", label: "Chat", visible: true },
    { id: "summary", label: "Summary", visible: true },
    { id: "transcription", label: "Transcription", visible: result.hasAudio },
    { id: "translation", label: "Translation", visible: result.isNonEnglish },
    { id: "visualization", label: "Visualization", visible: true },
  ]

  const visibleTabs = tabs.filter((tab) => tab.visible)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold">Analysis Results</h1>
            <p className="text-muted-foreground mt-1">{result.fileName}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onReset}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

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
            {activeTab === "chat" && <ChatTab fileName={result.fileName} />}
            {activeTab === "summary" && <SummaryTab summary={result.summary} />}
            {activeTab === "transcription" && result.hasAudio && (
              <TranscriptionTab transcription={result.transcription || ""} />
            )}
            {activeTab === "translation" && result.isNonEnglish && (
              <TranslationTab translation={result.translation || ""} />
            )}
            {activeTab === "visualization" && <VisualizationTab data={result.chartData} />}
          </div>
        </Card>

        {/* Metadata */}
        <Card className="p-4 bg-muted/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">File Name</p>
              <p className="font-medium">{result.fileName}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Uploaded</p>
              <p className="font-medium">{new Date(result.uploadedAt).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Has Audio</p>
              <p className="font-medium">{result.hasAudio ? "Yes" : "No"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Language</p>
              <p className="font-medium">{result.isNonEnglish ? "Non-English" : "English"}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
