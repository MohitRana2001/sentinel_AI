"use client";

import React, { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { UnifiedUpload } from "@/components/upload/unified-upload";
import { SuspectManagement } from "./suspect-management";
import { CaseGroupedJobs } from "./case-grouped-jobs";
import { useAuth } from "@/context/auth-context";
import type { MediaType, MediaItem, FileWithMetadata, Suspect } from "@/types";
import { FileText, Music, Video, Phone, Clock, CheckCircle, XCircle, Loader2, Users, History, Upload as UploadIcon, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { useRouter } from "next/navigation";
import { formatTime, formatProcessingStages, getTotalTime } from "@/lib/time-utils";

type DashboardTab = 'upload' | 'suspects' | 'history';

export function AnalystDashboard() {
  const { uploadJob, mediaItems } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<DashboardTab>("upload");
  const [suspects, setSuspects] = useState<Suspect[]>([]);
  const [pastJobs, setPastJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [cases, setCases] = useState<string[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);

  // Load past jobs on mount AND when switching to history tab
  useEffect(() => {
    if (activeTab === 'history') {
      loadPastJobs();
    }
  }, [activeTab]);

  // Load cases on mount
  useEffect(() => {
    async function loadCases() {
      try {
        const response = await apiClient.getCases();
        setCases(response.cases);
      } catch (error) {
        console.error("Failed to load cases:", error);
      }
    }
    loadCases();
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

  // Filter jobs by selected case
  const filteredJobs = selectedCase && selectedCase !== "all" 
    ? pastJobs.filter(job => job.case_name === selectedCase)
    : pastJobs;

  const handleUpload = async (files: FileWithMetadata[], jobSuspects: Suspect[], caseName?: string, parentJobId?: string) => {
    await uploadJob({ files, suspects: jobSuspects }, caseName, parentJobId);
  };

  const handleViewResults = (jobId: string) => {
    // Navigate to results page with the job ID
    router.push(`/results?jobId=${encodeURIComponent(jobId)}`);
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
                    
                    {/* Current Stage */}
                    {item.currentStage && item.status === 'processing' && (
                      <p className="text-blue-600 font-medium">
                        <Loader2 className="inline h-3 w-3 animate-spin mr-1" />
                        {item.currentStage.replace(/_/g, ' ')}
                      </p>
                    )}
                    
                    {/* Processing Progress */}
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
                    
                    {/* Processing Timing */}
                    {item.processingStages && Object.keys(item.processingStages).length > 0 && (
                      <div className="mt-2 p-2 bg-slate-50 rounded text-xs space-y-1">
                        <p className="font-medium text-slate-700">Processing Time:</p>
                        {Object.entries(item.processingStages).map(([stage, time]) => (
                          <p key={stage} className="text-slate-600">
                            • {stage.replace(/_/g, ' ')}: <span className="font-mono">{formatTime(time)}</span>
                          </p>
                        ))}
                        <p className="font-medium text-slate-700 pt-1 border-t">
                          Total: <span className="font-mono">{formatTime(getTotalTime(item.processingStages))}</span>
                        </p>
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
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <UploadIcon className="h-4 w-4" />
            Upload
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

        <TabsContent value="upload" className="mt-6">
          <div className="flex flex-col gap-6">
            <UnifiedUpload onUpload={handleUpload} suspects={suspects} />
            
            <Card>
              <CardHeader>
                <CardTitle>Recent Uploads</CardTitle>
                <CardDescription>
                  {mediaItems.length} item(s) uploaded
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MediaItemsList items={mediaItems.slice(0, 10)} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="suspects" className="mt-6">
          <SuspectManagement 
            suspects={suspects}
            onSuspectsChange={setSuspects}
          />
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

            {/* Case Filter */}
            {cases.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Filter className="h-4 w-4 text-muted-foreground" />
                    <Label htmlFor="case-filter" className="text-sm font-medium">
                      Filter by Case
                    </Label>
                    <Select 
                      value={selectedCase || "all"} 
                      onValueChange={(value) => setSelectedCase(value === "all" ? null : value)}
                    >
                      <SelectTrigger id="case-filter" className="w-[300px]">
                        <SelectValue placeholder="All Cases" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Cases</SelectItem>
                        {cases.map(caseName => (
                          <SelectItem key={caseName} value={caseName}>
                            {caseName}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedCase && selectedCase !== "all" && (
                      <span className="text-sm text-muted-foreground">
                        {filteredJobs.length} job(s) found
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {loadingJobs ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <Loader2 className="h-8 w-8 mx-auto animate-spin text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Loading jobs...</p>
                </CardContent>
              </Card>
            ) : filteredJobs.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">
                    {selectedCase && selectedCase !== "all" 
                      ? `No jobs found for case "${selectedCase}"` 
                      : "No past jobs found"}
                  </h3>
                  <p className="text-muted-foreground">
                    {selectedCase && selectedCase !== "all"
                      ? "Try selecting a different case or upload new files"
                      : "Your processing history will appear here"}
                  </p>
                </CardContent>
              </Card>
            ) : (
              <CaseGroupedJobs jobs={filteredJobs} onViewResults={handleViewResults} />
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
