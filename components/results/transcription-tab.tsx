"use client"
import { Card } from "@/components/ui/card"
import { Volume2 } from "lucide-react"

interface TranscriptionTabProps {
  transcription: string
}

export function TranscriptionTab({ transcription }: TranscriptionTabProps) {
  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Volume2 className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Audio Transcription</h3>
        </div>
        <div className="prose prose-sm max-w-none">
          <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">{transcription}</p>
        </div>
      </Card>

      <Card className="p-4 bg-green-50 border-green-200">
        <p className="text-sm text-green-900">
          <strong>Note:</strong> This transcription was extracted from the audio content in your document.
        </p>
      </Card>
    </div>
  )
}
