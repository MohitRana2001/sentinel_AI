"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/status-badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { ChevronRight, ChevronDown, Users, FileText, Calendar } from "lucide-react";
import Link from "next/link";

interface Job {
  job_id: string;
  case_name?: string;
  status: string;
  total_files: number;
  processed_files: number;
  progress_percentage: number;
  suspects_count?: number;
  created_at: string;
  parent_job_id?: string | null;
}

interface CaseGroupedJobsProps {
  jobs: Job[];
  onViewResults: (jobId: string) => void;
}

export function CaseGroupedJobs({ jobs, onViewResults }: CaseGroupedJobsProps) {
  const [openCases, setOpenCases] = useState<Record<string, boolean>>({});

  // Group jobs by case
  const jobsByCase: Record<string, Job[]> = {};
  const uncategorizedJobs: Job[] = [];

  jobs.forEach(job => {
    if (job.case_name) {
      if (!jobsByCase[job.case_name]) {
        jobsByCase[job.case_name] = [];
      }
      jobsByCase[job.case_name].push(job);
    } else {
      uncategorizedJobs.push(job);
    }
  });

  const toggleCase = (caseName: string) => {
    setOpenCases(prev => ({
      ...prev,
      [caseName]: !prev[caseName]
    }));
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

  const renderJob = (job: Job) => (
    <div
      key={job.job_id}
      className={`flex items-center gap-4 p-4 border-b last:border-b-0 hover:bg-slate-50 transition-colors ${
        job.parent_job_id ? "ml-6 border-l-2 border-l-blue-300" : ""
      }`}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          {job.parent_job_id && (
            <span className="text-muted-foreground text-sm">↳</span>
          )}
          <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
            {job.job_id}
          </code>
          <StatusBadge status={job.status as any} />
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {job.processed_files}/{job.total_files} files
          </span>
          {job.suspects_count && job.suspects_count > 0 && (
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {job.suspects_count} suspect(s)
            </span>
          )}
          <span>{Math.round(job.progress_percentage)}% complete</span>
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {formatDate(job.created_at)}
          </span>
        </div>
      </div>
      {job.status === "completed" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onViewResults(job.job_id)}
        >
          View Results
        </Button>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Cases with jobs */}
      {Object.entries(jobsByCase).map(([caseName, caseJobs]) => (
        <Collapsible
          key={caseName}
          open={openCases[caseName] !== false}
          onOpenChange={() => toggleCase(caseName)}
        >
          <Card>
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {openCases[caseName] !== false ? (
                      <ChevronDown className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    )}
                    <CardTitle className="text-base font-semibold">
                      📁 Case: {caseName}
                    </CardTitle>
                    <Badge variant="secondary">
                      {caseJobs.length} job{caseJobs.length === 1 ? '' : 's'}
                    </Badge>
                  </div>
                  <Button variant="ghost" size="sm" asChild onClick={(e) => e.stopPropagation()}>
                    <Link href={`/cases/${encodeURIComponent(caseName)}`}>
                      View Case →
                    </Link>
                  </Button>
                </div>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent className="pt-0">
                <div className="border rounded-lg overflow-hidden">
                  {caseJobs.map(renderJob)}
                </div>
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      ))}

      {/* Uncategorized jobs */}
      {uncategorizedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-semibold text-muted-foreground">
                Uncategorized Jobs
              </CardTitle>
              <Badge variant="outline">
                {uncategorizedJobs.length} job{uncategorizedJobs.length === 1 ? '' : 's'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              {uncategorizedJobs.map(renderJob)}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {Object.keys(jobsByCase).length === 0 && uncategorizedJobs.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No jobs found</h3>
            <p className="text-muted-foreground">
              Your processing history will appear here
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
