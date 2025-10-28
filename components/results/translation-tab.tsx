"use client"
import { Card } from "@/components/ui/card"
import { Globe } from "lucide-react"

interface TranslationTabProps {
  translation: string
}

export function TranslationTab({ translation }: TranslationTabProps) {
  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">English Translation</h3>
        </div>
        <div className="prose prose-sm max-w-none">
          <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">{translation}</p>
        </div>
      </Card>

      <Card className="p-4 bg-purple-50 border-purple-200">
        <p className="text-sm text-purple-900">
          <strong>Note:</strong> This is an AI-generated translation of the non-English content detected in your
          document.
        </p>
      </Card>
    </div>
  )
}
