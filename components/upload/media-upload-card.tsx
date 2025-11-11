"use client";

import React, { useState, useCallback } from "react";
import { Upload, FileText, Music, Video, Loader2, Phone } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import type { MediaType } from "@/types";

// Languages from document_processor.py LANGUAGE_MAPPING
const SUPPORTED_LANGUAGES = [
  { code: 'hi', name: 'Hindi', tesseract: 'hin' },
  { code: 'bn', name: 'Bengali', tesseract: 'ben' },
  { code: 'pa', name: 'Punjabi', tesseract: 'pan' },
  { code: 'gu', name: 'Gujarati', tesseract: 'guj' },
  { code: 'kn', name: 'Kannada', tesseract: 'kan' },
  { code: 'ml', name: 'Malayalam', tesseract: 'mal' },
  { code: 'mr', name: 'Marathi', tesseract: 'mar' },
  { code: 'ta', name: 'Tamil', tesseract: 'tam' },
  { code: 'te', name: 'Telugu', tesseract: 'tel' },
  { code: 'zh', name: 'Chinese (Simplified)', tesseract: 'chi_sim' },
  { code: 'en', name: 'English', tesseract: 'eng' },
] as const;

interface MediaUploadCardProps {
  mediaType: MediaType;
  onUpload: (file: File, language?: string) => Promise<void>;
  isUploading?: boolean;
}

const MEDIA_CONFIG = {
  document: {
    icon: FileText,
    title: "Upload Document",
    description: "PDF, DOCX files supported. Language will be auto-detected using langid.",
    accept: ".pdf,.docx",
    maxSize: 50, // MB
    showLanguageSelect: false,
  },
  audio: {
    icon: Music,
    title: "Upload Audio",
    description: "MP3, WAV, M4A files supported. Select source language for transcription.",
    accept: ".mp3,.wav,.m4a,.ogg",
    maxSize: 100, // MB
    showLanguageSelect: true,
  },
  video: {
    icon: Video,
    title: "Upload Video",
    description: "MP4, AVI, MOV files supported. Select spoken language for transcription.",
    accept: ".mp4,.avi,.mov,.mkv",
    maxSize: 500, // MB
    showLanguageSelect: true,
  },
  cdr: {
    icon: Phone,
    title: "Upload CDR (Call Data Record)",
    description: "CSV, XLS, XLSX files supported. Standard telecom CDR format expected.",
    accept: ".csv,.xls,.xlsx",
    maxSize: 100, // MB
    showLanguageSelect: false,
  },
};

export function MediaUploadCard({ mediaType, onUpload, isUploading = false }: MediaUploadCardProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const { toast } = useToast();

  const config = MEDIA_CONFIG[mediaType];
  const Icon = config.icon;

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const validateFile = (file: File): boolean => {
    const maxSizeBytes = config.maxSize * 1024 * 1024;
    
    if (file.size > maxSizeBytes) {
      toast({
        title: "File too large",
        description: `Maximum file size is ${config.maxSize}MB`,
        variant: "destructive",
      });
      return false;
    }

    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!config.accept.includes(fileExtension)) {
      toast({
        title: "Invalid file type",
        description: `Only ${config.accept} files are supported`,
        variant: "destructive",
      });
      return false;
    }

    return true;
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && validateFile(files[0])) {
      setSelectedFile(files[0]);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0 && validateFile(files[0])) {
      setSelectedFile(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    // Validate language selection for audio/video
    if (config.showLanguageSelect && !selectedLanguage) {
      toast({
        title: "Language required",
        description: "Please select the source language",
        variant: "destructive",
      });
      return;
    }

    try {
      await onUpload(selectedFile, selectedLanguage || undefined);
      setSelectedFile(null);
      setSelectedLanguage("");
      toast({
        title: "Upload successful",
        description: `${selectedFile.name} is being processed`,
      });
    } catch (error) {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-primary" />
          <CardTitle>{config.title}</CardTitle>
        </div>
        <CardDescription>{config.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drag & Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          `}
        >
          <input
            type="file"
            id={`file-upload-${mediaType}`}
            className="hidden"
            accept={config.accept}
            onChange={handleFileSelect}
            disabled={isUploading}
          />
          <label htmlFor={`file-upload-${mediaType}`} className="cursor-pointer">
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">
              {selectedFile ? (
                <span className="font-medium text-foreground">{selectedFile.name}</span>
              ) : (
                <>
                  Drag & drop or <span className="text-primary font-medium">browse</span>
                </>
              )}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Max size: {config.maxSize}MB
            </p>
          </label>
        </div>

        {/* Language Selection (for audio/video only) */}
        {config.showLanguageSelect && selectedFile && (
          <div className="space-y-2">
            <Label htmlFor={`language-select-${mediaType}`}>Source Language *</Label>
            <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
              <SelectTrigger id={`language-select-${mediaType}`}>
                <SelectValue placeholder="Select language..." />
              </SelectTrigger>
              <SelectContent>
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code}>
                    {lang.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Upload Button */}
        <Button
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
          className="w-full"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload {mediaType}
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
