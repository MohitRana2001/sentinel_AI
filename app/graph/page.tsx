"use client";
import { useAuth } from "@/context/auth-context";
import { Header } from "@/components/common/header";
import { GraphVisualization } from "@/components/results/graph-visualization";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function GraphPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/");
      return;
    }

    if (!jobId) {
      router.push("/dashboard");
      return;
    }
  }, [isAuthenticated, jobId, router]);

  if (!isAuthenticated || !jobId) {
    return null;
  }

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Knowledge Graph</h1>
              <p className="text-muted-foreground mt-1">
                Visualize entities and relationships from Job{" "}
                {jobId.slice(0, 8)}…
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/dashboard")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
          <GraphVisualization jobId={jobId} />
        </div>
      </div>
    </>
  );
}
