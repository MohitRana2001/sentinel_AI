"use client";

import { Badge } from "@/components/ui/badge"
import { Loader2, CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react"

interface StatusBadgeProps {
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'awaiting_graph'
  currentStage?: string
  className?: string
}

const STAGE_LABELS: Record<string, string> = {
  starting: "Initializing",
  extraction: "Extracting text",
  transcription: "Transcribing audio",
  frame_extraction: "Extracting frames",
  video_analysis: "Analyzing video",
  translation: "Translating",
  summarization: "Summarizing",
  embeddings: "Creating embeddings",
  vectorization: "Vectorizing",
  awaiting_graph: "Awaiting graph",
  graph_building: "Building graph",
  completed: "Completed"
}

export function StatusBadge({ status, currentStage, className }: StatusBadgeProps) {
  const variants = {
    queued: { 
      variant: "secondary" as const, 
      icon: Clock, 
      text: "Queued",
      className: "bg-gray-100 text-gray-700 hover:bg-gray-200"
    },
    processing: { 
      variant: "default" as const, 
      icon: Loader2, 
      text: currentStage ? STAGE_LABELS[currentStage] || currentStage.replace(/_/g, ' ') : "Processing",
      className: "bg-blue-100 text-blue-700 hover:bg-blue-200"
    },
    awaiting_graph: { 
      variant: "default" as const, 
      icon: AlertCircle, 
      text: "Awaiting Graph",
      className: "bg-orange-100 text-orange-700 hover:bg-orange-200"
    },
    completed: { 
      variant: "success" as const, 
      icon: CheckCircle2, 
      text: "Completed",
      className: "bg-green-100 text-green-700 hover:bg-green-200"
    },
    failed: { 
      variant: "destructive" as const, 
      icon: XCircle, 
      text: "Failed",
      className: "bg-red-100 text-red-700 hover:bg-red-200"
    }
  }
  
  const config = variants[status] || variants.queued
  const Icon = config.icon
  
  return (
    <Badge variant={config.variant} className={`flex items-center gap-1.5 ${config.className} ${className || ''}`}>
      <Icon className={`h-3 w-3 ${status === 'processing' ? 'animate-spin' : ''}`} />
      <span className="capitalize">{config.text}</span>
    </Badge>
  )
}
