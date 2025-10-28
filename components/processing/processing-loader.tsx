"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"

interface ProcessingLoaderProps {
  onComplete: () => void
}

export function ProcessingLoader({ onComplete }: ProcessingLoaderProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Simulate processing with progress updates
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setTimeout(onComplete, 500)
          return 100
        }
        return prev + Math.random() * 30
      })
    }, 600)

    return () => clearInterval(interval)
  }, [onComplete])

  const messages = [
    "Analyzing document...",
    "Extracting text...",
    "Processing audio...",
    "Generating summary...",
    "Finalizing results...",
  ]

  const messageIndex = Math.floor((progress / 100) * (messages.length - 1))

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <div className="p-8 text-center space-y-6">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Processing Your Document</h2>
            <p className="text-sm text-muted-foreground">{messages[messageIndex]}</p>
          </div>

          <div className="space-y-2">
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{Math.round(Math.min(progress, 100))}%</p>
          </div>

          <div className="flex justify-center gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-primary animate-pulse"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
