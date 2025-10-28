"use client"
import { Card } from "@/components/ui/card"

interface SummaryTabProps {
  summary: string
}

export function SummaryTab({ summary }: SummaryTabProps) {
  return (
    <div className="space-y-4">
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Document Summary</h3>
        <div className="prose prose-sm max-w-none">
          <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">{summary}</p>
        </div>
      </Card>

      <Card className="p-4 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-900">
          <strong>Tip:</strong> This summary was automatically generated from the document content using AI analysis.
        </p>
      </Card>
    </div>
  )
}
