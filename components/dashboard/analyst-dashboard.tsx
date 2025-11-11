"use client";

import React, { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MediaUploadCard } from "@/components/upload/media-upload-card";
import { SuspectManagement } from "./suspect-management";
import { useAuth } from "@/context/auth-context";
import type { MediaType, MediaItem } from "@/types";
import { FileText, Music, Video, Phone, Clock, CheckCircle, XCircle, Loader2, Users, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";

type DashboardTab = MediaType | 'suspects' | 'history';

export function AnalystDashboard() {
  const { uploadMedia, mediaItems } = useAuth();
  const [activeTab, setActiveTab] = useState<DashboardTab>("document");
  const [uploading, setUploading] = useState<Record<MediaType, boolean>>({
    document: false,
    audio: false,
    video: false,
    cdr: false,
  });
  const [pastJobs, setPastJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);

  // Load past jobs on mount
  useEffect(() => {
    loadPastJobs();
  }, []);

  const loadPastJobs = async () => {
    try {
      setLoadingJobs(true);
      const jobs = await apiClient.getAnalystJobs(15, 0);
      setPastJobs(jobs);
    } catch (err) {
      console.error("Failed to load past jobs:", err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleUpload = (mediaType: MediaType) => {
    return async (file: File, language?: string) => {
      setUploading(prev => ({ ...prev, [mediaType]: true }));
      try {
        await uploadMedia(file, mediaType, language);
      } catch (error) {
        console.error(`Upload failed:`, error);
        throw error;
      } finally {
        setUploading(prev => ({ ...prev, [mediaType]: false }));
      }
    };
  };

  const getMediaItemsByType = (type: MediaType): MediaItem[] => {
    return mediaItems.filter(item => item.mediaType === type);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'queued':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-IN", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "bg-green-100 text-green-700";
      case "processing":
        return "bg-blue-100 text-blue-700";
      case "failed":
        return "bg-red-100 text-red-700";
      default:
        return "bg-yellow-100 text-yellow-700";
    }
  };

  const MediaItemsList = ({ items }: { items: MediaItem[] }) => {
    if (items.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <p>No items uploaded yet</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {items.map((item) => (
          <Card key={item.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusIcon(item.status)}
                    <h4 className="font-medium">{item.fileName}</h4>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Size: {item.fileSize.toFixed(2)} MB</p>
                    {item.language && <p>Language: {item.language}</p>}
                    {item.status === 'processing' && item.progress !== undefined && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between mb-1">
                          <span>Progress</span>
                          <span>{item.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${item.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {item.status === 'completed' && item.summary && (
                      <div className="mt-2 p-2 bg-muted rounded">
                        <p className="text-xs font-medium mb-1">Summary:</p>
                        <p className="text-xs line-clamp-3">{item.summary}</p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="ml-4">
                  <span className={`
                    px-2 py-1 text-xs rounded-full
                    ${item.status === 'completed' ? 'bg-green-100 text-green-800' : ''}
                    ${item.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
                    ${item.status === 'processing' ? 'bg-blue-100 text-blue-800' : ''}
                    ${item.status === 'queued' ? 'bg-yellow-100 text-yellow-800' : ''}
                  `}>
                    {item.status}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analyst Dashboard</h1>
        <p className="text-muted-foreground">
          Upload and analyze documents, audio, and video files
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as DashboardTab)}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="document" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="audio" className="flex items-center gap-2">
            <Music className="h-4 w-4" />
            Audio
          </TabsTrigger>
          <TabsTrigger value="video" className="flex items-center gap-2">
            <Video className="h-4 w-4" />
            Video
          </TabsTrigger>
          <TabsTrigger value="cdr" className="flex items-center gap-2">
            <Phone className="h-4 w-4" />
            CDR
          </TabsTrigger>
          <TabsTrigger value="suspects" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Suspects
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="document" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <MediaUploadCard
                mediaType="document"
                onUpload={handleUpload("document")}
                isUploading={uploading.document}
              />
            </div>
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded Documents</CardTitle>
                  <CardDescription>
                    {getMediaItemsByType('document').length} document(s) uploaded
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <MediaItemsList items={getMediaItemsByType('document')} />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="audio" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <MediaUploadCard
                mediaType="audio"
                onUpload={handleUpload("audio")}
                isUploading={uploading.audio}
              />
            </div>
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded Audio Files</CardTitle>
                  <CardDescription>
                    {getMediaItemsByType('audio').length} audio file(s) uploaded
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <MediaItemsList items={getMediaItemsByType('audio')} />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="video" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <MediaUploadCard
                mediaType="video"
                onUpload={handleUpload("video")}
                isUploading={uploading.video}
              />
            </div>
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded Video Files</CardTitle>
                  <CardDescription>
                    {getMediaItemsByType('video').length} video file(s) uploaded
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <MediaItemsList items={getMediaItemsByType('video')} />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="cdr" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <MediaUploadCard
                mediaType="cdr"
                onUpload={handleUpload("cdr")}
                isUploading={uploading.cdr}
              />
            </div>
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded CDR Files</CardTitle>
                  <CardDescription>
                    {getMediaItemsByType('cdr').length} CDR file(s) uploaded
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <MediaItemsList items={getMediaItemsByType('cdr')} />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="suspects" className="mt-6">
          <SuspectManagement />
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Past Jobs</h2>
                <p className="text-muted-foreground">
                  View and manage your previous processing jobs
                </p>
              </div>
              <Button variant="outline" onClick={loadPastJobs} disabled={loadingJobs}>
                <Clock className="mr-2 h-4 w-4" />
                {loadingJobs ? 'Loading...' : 'Refresh'}
              </Button>
            </div>

            {loadingJobs ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <Loader2 className="h-8 w-8 mx-auto animate-spin text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Loading jobs...</p>
                </CardContent>
              </Card>
            ) : pastJobs.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No past jobs found</h3>
                  <p className="text-muted-foreground">
                    Your processing history will appear here
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {pastJobs.map((job) => (
                  <Card
                    key={job.job_id}
                    className="hover:shadow-lg transition-shadow"
                  >
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                              {job.job_id}
                            </code>
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                                job.status
                              )}`}
                            >
                              {job.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>
                              {job.processed_files}/{job.total_files} files
                            </span>
                            <span>
                              {Math.round(job.progress_percentage)}% complete
                            </span>
                            <span>{formatDate(job.created_at)}</span>
                          </div>
                        </div>
                        {job.status === "completed" && (
                          <Button variant="outline">
                            View Results
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
