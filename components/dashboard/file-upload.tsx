"use client"

import type React from "react"
import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Upload } from "lucide-react"

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  isDisabled?: boolean
}

export function FileUpload({ onFilesSelected, isDisabled = false }: FileUploadProps) {
  const [isDragActive, setIsDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isDisabled) {
      setIsDragActive(e.type === "dragenter" || e.type === "dragover")
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)

    if (!isDisabled && e.dataTransfer.files) {
      const files = Array.from(e.dataTransfer.files)
      onFilesSelected(files)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      onFilesSelected(files)
    }
  }

  const handleClick = () => {
    if (!isDisabled) {
      fileInputRef.current?.click()
    }
  }

  return (
    <Card
      className={`border-2 border-dashed transition-all ${
        isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50"
      } ${isDisabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <div className="p-12 text-center">
        <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">Upload Documents</h3>
        <p className="text-sm text-muted-foreground mb-4">Drag and drop your files here, or click to browse</p>
        <p className="text-xs text-muted-foreground mb-6">Supported: PDF, DOCX, TXT, MP3, WAV, and more</p>
        <Button disabled={isDisabled}>Select Files</Button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileChange}
        className="hidden"
        accept=".pdf,.docx,.txt,.mp3,.wav,.m4a,.ogg,.flac"
        disabled={isDisabled}
      />
    </Card>
  )
}
