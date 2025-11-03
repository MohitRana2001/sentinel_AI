"use client";
import { Card } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface SummaryTabProps {
  documents: Array<{
    id: number;
    fileName: string;
    summary: string;
  }>;
}

export function SummaryTab({ documents }: SummaryTabProps) {
  return (
    <div className="space-y-4">
      {documents.map((doc) => (
        <Card key={doc.id} className="p-6">
          <h3 className="text-lg font-semibold mb-4">{doc.fileName}</h3>
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {doc.summary}
            </ReactMarkdown>
          </div>
        </Card>
      ))}

      {documents.length === 0 && (
        <Card className="p-6">
          <p className="text-muted-foreground">
            No documents selected. Please select documents from above to view
            their summaries.
          </p>
        </Card>
      )}

      {documents.length > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <p className="text-sm text-blue-900">
            <strong>Tip:</strong>{" "}
            {documents.length === 1
              ? "This summary was"
              : "These summaries were"}{" "}
            automatically generated from the document content using AI analysis.
          </p>
        </Card>
      )}
    </div>
  );
}
