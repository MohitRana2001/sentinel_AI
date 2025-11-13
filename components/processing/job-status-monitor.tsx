"use client";

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { StatusBadge } from "@/components/common/status-badge"
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react"

interface ArtifactStatus {
  filename: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'awaiting_graph'
  current_stage?: string
  processing_stages?: Record<string, number>
  error_message?: string
  progress?: number
}

interface JobStatusMonitorProps {
  jobId: string
}

const STAGE_ORDER = [
  'starting',
  'extraction',
  'transcription',
  'frame_extraction',
  'video_analysis',
  'translation',
  'summarization',
  'embeddings',
  'vectorization',
  'awaiting_graph',
  'graph_building',
  'completed'
]

export function JobStatusMonitor({ jobId }: JobStatusMonitorProps) {
  const [artifacts, setArtifacts] = useState<Record<string, ArtifactStatus>>({})
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Connect to SSE stream for real-time updates
    const eventSource = new EventSource(`/api/jobs/${jobId}/status/stream`)
    
    eventSource.onopen = () => {
      setIsConnected(true)
    }
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'artifact_status') {
          setArtifacts(prev => ({
            ...prev,
            [data.filename]: {
              filename: data.filename,
              status: data.status,
              current_stage: data.current_stage,
              processing_stages: data.processing_stages,
              error_message: data.error_message,
              progress: data.progress
            }
          }))
        }
      } catch (error) {
        console.error('Error parsing SSE message:', error)
      }
    }
    
    eventSource.onerror = () => {
      setIsConnected(false)
      eventSource.close()
    }
    
    return () => eventSource.close()
  }, [jobId])

  const calculateProgress = (artifact: ArtifactStatus): number => {
    if (artifact.progress !== undefined) return artifact.progress
    if (!artifact.current_stage) return 0
    
    const currentIndex = STAGE_ORDER.indexOf(artifact.current_stage)
    if (currentIndex === -1) return 0
    
    return Math.round(((currentIndex + 1) / STAGE_ORDER.length) * 100)
  }

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Processing Status</h3>
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span className="text-xs text-muted-foreground">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      {Object.keys(artifacts).length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Waiting for processing updates...</p>
          </CardContent>
        </Card>
      ) : (
        Object.values(artifacts).map(artifact => (
          <Card key={artifact.filename}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium truncate flex-1">
                  {artifact.filename}
                </CardTitle>
                <StatusBadge status={artifact.status} currentStage={artifact.current_stage} />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Progress Bar */}
              {(artifact.status === 'processing' || artifact.status === 'awaiting_graph') && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span>{calculateProgress(artifact)}%</span>
                  </div>
                  <Progress value={calculateProgress(artifact)} className="h-2" />
                </div>
              )}
              
              {/* Current Stage */}
              {artifact.status === 'processing' && artifact.current_stage && (
                <div className="flex items-center gap-2 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-muted-foreground capitalize">
                    {artifact.current_stage.replace(/_/g, ' ')}...
                  </span>
                </div>
              )}
              
              {/* Processing Timing Breakdown */}
              {artifact.processing_stages && Object.keys(artifact.processing_stages).length > 0 && (
                <div className="mt-3 p-3 bg-slate-50 rounded-lg space-y-1.5">
                  <p className="text-xs font-medium text-slate-700">Timing Breakdown:</p>
                  <div className="space-y-1">
                    {Object.entries(artifact.processing_stages).map(([stage, time]) => (
                      <div key={stage} className="flex justify-between text-xs">
                        <span className="text-slate-600 capitalize">{stage.replace(/_/g, ' ')}:</span>
                        <span className="font-mono text-slate-700">{formatTime(time)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 border-t border-slate-200 flex justify-between text-xs font-medium">
                    <span className="text-slate-700">Total:</span>
                    <span className="font-mono text-slate-800">
                      {formatTime(Object.values(artifact.processing_stages).reduce((a, b) => a + b, 0))}
                    </span>
                  </div>
                </div>
              )}
              
              {/* Completed */}
              {artifact.status === 'completed' && (
                <div className="flex items-center gap-2 text-green-600 text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Completed successfully</span>
                </div>
              )}
              
              {/* Failed */}
              {artifact.status === 'failed' && artifact.error_message && (
                <div className="flex items-start gap-2 text-red-600 text-sm">
                  <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <span className="flex-1">{artifact.error_message}</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}
