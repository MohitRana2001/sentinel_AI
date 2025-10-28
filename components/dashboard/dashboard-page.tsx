"use client"

import { useState } from "react"
import { FileUpload } from "./file-upload"
import { ProcessingLoader } from "@/components/processing/processing-loader"
import { ResultsContainer } from "@/components/results/results-container"
import { Sidebar } from "@/components/common/sidebar"
import { PastUploads } from "@/components/sidebar/past-uploads"
import { SettingsPage } from "@/components/sidebar/settings-page"
import { ProfilePage } from "@/components/sidebar/profile-page"
import { useAuth } from "@/context/auth-context"
import type { AnalysisResult } from "@/types"

type AppState = "upload" | "processing" | "results"
type CurrentPage = "analysis" | "history" | "settings" | "profile"

// Dummy analysis result
const DUMMY_ANALYSIS_RESULT: AnalysisResult = {
  id: "analysis-001",
  fileName: "quarterly-report.pdf",
  uploadedAt: new Date().toISOString(),
  summary:
    "This comprehensive quarterly business report details the company's financial performance, operational metrics, and strategic initiatives for Q3 2024. Key highlights include a 15% revenue increase year-over-year, successful expansion into three new markets, and the launch of two innovative product lines. The report also covers risk assessments, competitive analysis, and forward-looking projections for the remainder of the fiscal year.",
  transcription:
    "Welcome to the quarterly earnings call. Thank you all for joining us today. We're pleased to report strong financial results across all business segments. Revenue grew 15% year-over-year, driven primarily by our core products and new market expansion. Operating margins improved by 2.3 percentage points due to operational efficiencies. Looking ahead, we remain confident in our growth trajectory and are investing heavily in R&D and market development.",
  translation:
    "Bienvenue à l'appel de résultats trimestriels. Merci à tous de nous avoir rejoints aujourd'hui. Nous sommes heureux de signaler des résultats financiers solides dans tous les segments commerciaux. Les revenus ont augmenté de 15% d'une année à l'autre, tirés principalement par nos produits de base et l'expansion sur de nouveaux marchés.",
  hasAudio: true,
  isNonEnglish: true,
  chartData: [
    { name: "Q1", value: 45, category: "Revenue" },
    { name: "Q2", value: 52, category: "Revenue" },
    { name: "Q3", value: 61, category: "Revenue" },
    { name: "Q4 (Projected)", value: 68, category: "Revenue" },
  ],
}

export function DashboardPage() {
  const [appState, setAppState] = useState<AppState>("upload")
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [currentPage, setCurrentPage] = useState<CurrentPage>("analysis")
  const { addDocument } = useAuth()

  const handleFilesSelected = (files: File[]) => {
    setSelectedFiles(files)
    setAppState("processing")
  }

  const handleProcessingComplete = () => {
    if (selectedFiles.length > 0) {
      addDocument({
        id: `doc-${Date.now()}`,
        fileName: selectedFiles[0].name,
        uploadedAt: new Date().toISOString(),
        fileSize: Number.parseFloat((selectedFiles[0].size / (1024 * 1024)).toFixed(2)),
        status: "completed",
      })
    }
    setAppState("results")
  }

  const handleReset = () => {
    setAppState("upload")
    setSelectedFiles([])
  }

  const handleSelectDocument = (docId: string) => {
    setCurrentPage("analysis")
  }

  return (
    <div className="flex">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />

      {/* Main Content */}
      <div className="flex-1 ml-0">
        {currentPage === "analysis" && (
          <>
            {appState === "upload" && (
              <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
                <div className="max-w-2xl mx-auto">
                  <div className="mb-8">
                    <h1 className="text-4xl font-bold mb-2">Document Analysis</h1>
                    <p className="text-muted-foreground">
                      Upload your documents to get instant AI-powered analysis, transcription, and insights.
                    </p>
                  </div>
                  <FileUpload onFilesSelected={handleFilesSelected} />
                </div>
              </div>
            )}

            {appState === "processing" && <ProcessingLoader onComplete={handleProcessingComplete} />}

            {appState === "results" && <ResultsContainer result={DUMMY_ANALYSIS_RESULT} onReset={handleReset} />}
          </>
        )}

        {currentPage === "history" && <PastUploads onSelectDocument={handleSelectDocument} />}

        {currentPage === "settings" && <SettingsPage />}

        {currentPage === "profile" && <ProfilePage />}
      </div>
    </div>
  )
}
