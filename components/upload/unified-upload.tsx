"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Upload, FileText, Music, Video, Phone, X, Loader2, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { MediaType, FileWithMetadata, Suspect } from "@/types";

// Languages from document_processor.py
const SUPPORTED_LANGUAGES = [
  { code: 'hi', name: 'Hindi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'pa', name: 'Punjabi' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'kn', name: 'Kannada' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'mr', name: 'Marathi' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'zh', name: 'Chinese (Simplified)' },
  { code: 'en', name: 'English' },
] as const;

const MEDIA_TYPE_CONFIG = {
  document: { icon: FileText, label: "Document", accept: ".pdf,.docx", needsLanguage: false },
  audio: { icon: Music, label: "Audio", accept: ".mp3,.wav,.m4a,.ogg", needsLanguage: true },
  video: { icon: Video, label: "Video", accept: ".mp4,.avi,.mov,.mkv", needsLanguage: true },
  cdr: { icon: Phone, label: "CDR", accept: ".csv,.xls,.xlsx", needsLanguage: false },
};

interface UnifiedUploadProps {
  onUpload: (files: FileWithMetadata[], suspects: Suspect[]) => Promise<void>;
  suspects: Suspect[];
}

export function UnifiedUpload({ onUpload, suspects }: UnifiedUploadProps) {
  const [files, setFiles] = useState<FileWithMetadata[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  const addFile = (mediaType: MediaType) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = MEDIA_TYPE_CONFIG[mediaType].accept;
    input.multiple = true;
    
    input.onchange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      const selectedFiles = Array.from(target.files || []);
      
      const newFiles: FileWithMetadata[] = selectedFiles.map(file => ({
        file,
        mediaType,
        language: undefined
      }));
      
      setFiles(prev => [...prev, ...newFiles]);
    };
    
    input.click();
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const updateLanguage = (index: number, language: string) => {
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, language } : f
    ));
  };

  const validateAndUpload = async () => {
    if (files.length === 0) {
      toast({
        title: "No files selected",
        description: "Please add at least one file to upload",
        variant: "destructive",
      });
      return;
    }

    // Validate language selection for audio/video
    for (const fileWithMeta of files) {
      if (MEDIA_TYPE_CONFIG[fileWithMeta.mediaType].needsLanguage && !fileWithMeta.language) {
        toast({
          title: "Language required",
          description: `Please select language for ${fileWithMeta.file.name}`,
          variant: "destructive",
        });
        return;
      }
    }

    setIsUploading(true);
    try {
      await onUpload(files, suspects);
      setFiles([]);
      toast({
        title: "Upload successful",
        description: `${files.length} file(s) uploaded and queued for processing`,
      });
    } catch (error) {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const getIcon = (mediaType: MediaType) => {
    const Icon = MEDIA_TYPE_CONFIG[mediaType].icon;
    return <Icon className="h-4 w-4" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Files & Suspects</CardTitle>
        <CardDescription>
          Add multiple files of different types to one job. Suspects will be included automatically.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add File Buttons */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Button
            variant="outline"
            onClick={() => addFile('document')}
            disabled={isUploading}
          >
            <FileText className="h-4 w-4 mr-2" />
            Add Document
          </Button>
          <Button
            variant="outline"
            onClick={() => addFile('audio')}
            disabled={isUploading}
          >
            <Music className="h-4 w-4 mr-2" />
            Add Audio
          </Button>
          <Button
            variant="outline"
            onClick={() => addFile('video')}
            disabled={isUploading}
          >
            <Video className="h-4 w-4 mr-2" />
            Add Video
          </Button>
          <Button
            variant="outline"
            onClick={() => addFile('cdr')}
            disabled={isUploading}
          >
            <Phone className="h-4 w-4 mr-2" />
            Add CDR
          </Button>
        </div>

        {/* Files List */}
        {files.length > 0 && (
          <div className="space-y-2">
            <Label>Files to Upload ({files.length})</Label>
            <div className="border rounded-lg divide-y max-h-64 overflow-y-auto">
              {files.map((fileWithMeta, index) => (
                <div key={index} className="p-3 flex items-center gap-3">
                  <div className="flex-shrink-0">
                    {getIcon(fileWithMeta.mediaType)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {fileWithMeta.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {MEDIA_TYPE_CONFIG[fileWithMeta.mediaType].label} • {(fileWithMeta.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  
                  {/* Language Selector for Audio/Video */}
                  {MEDIA_TYPE_CONFIG[fileWithMeta.mediaType].needsLanguage && (
                    <div className="w-40">
                      <Select
                        value={fileWithMeta.language || ""}
                        onValueChange={(lang) => updateLanguage(index, lang)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Language" />
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
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                    disabled={isUploading}
                  >
                    <X className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suspects Summary */}
        {suspects.length > 0 && (
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm font-medium mb-1">
              {suspects.length} Suspect(s) will be included in this job
            </p>
            <p className="text-xs text-muted-foreground">
              {suspects.map(s => s.fields.find(f => f.key.toLowerCase() === 'name')?.value || 'Unnamed').join(', ')}
            </p>
          </div>
        )}

        {/* Upload Button */}
        <Button
          onClick={validateAndUpload}
          disabled={files.length === 0 || isUploading}
          className="w-full"
          size="lg"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading {files.length} file(s)...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload {files.length} File(s) {suspects.length > 0 && `+ ${suspects.length} Suspect(s)`}
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
