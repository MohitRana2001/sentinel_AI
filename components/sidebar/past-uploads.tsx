"use client"

import { useAuth } from "@/context/auth-context"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, Download, Trash2, Clock } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface PastUploadsProps {
  onSelectDocument: (docId: string) => void
}

export function PastUploads({ onSelectDocument }: PastUploadsProps) {
  const { documents } = useAuth()

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase()
    return <FileText className="h-5 w-5" />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Past Uploads</h1>
          <p className="text-muted-foreground">Access and review your previously uploaded documents</p>
        </div>

        {documents.length === 0 ? (
          <Card className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No documents uploaded yet</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="p-2 bg-blue-100 rounded-lg">{getFileIcon(doc.fileName)}</div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm">{doc.fileName}</h3>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(doc.uploadedAt), { addSuffix: true })}
                        </span>
                        <span>{doc.fileSize} MB</span>
                        <span
                          className={`px-2 py-1 rounded ${doc.status === "completed" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => onSelectDocument(doc.id)}>
                      View
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
