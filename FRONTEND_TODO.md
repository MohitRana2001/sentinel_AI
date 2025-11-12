# UI Implementation Tasks - Artifact Status & Case Features

## 🎯 Overview
This document outlines the frontend changes needed to support the new artifact status tracking and case-based workflow features.

---

## ✅ COMPLETED (Backend)

1. ✅ Artifact status tracking across all media types (document/audio/video)
2. ✅ Mandatory case name validation
3. ✅ Real-time status updates via Redis pub/sub
4. ✅ Cross-document entity linking
5. ✅ Case-based API endpoints

---

## 🔨 TODO (Frontend)

### 1. **Analyst Dashboard - Vertical Stacking**

**File:** `/components/dashboard/analyst-dashboard.tsx`

**Current Issue:** Components are in a grid layout  
**Required Change:** Stack components vertically

**Implementation:**
```tsx
// Change from:
<div className="grid grid-cols-2 gap-4">
  {/* components */}
</div>

// To:
<div className="flex flex-col gap-4">
  {/* components */}
</div>
```

**Components to stack (top to bottom):**
1. Upload Section
2. Case Filter (NEW)
3. Job Statistics
4. Recent Jobs List

---

### 2. **Case Name Filter - Dashboard**

**File:** `/components/dashboard/analyst-dashboard.tsx`

**Add Case Filter Component:**
```tsx
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"

// Add state
const [selectedCase, setSelectedCase] = useState<string | null>(null)
const [cases, setCases] = useState<string[]>([])

// Fetch cases
useEffect(() => {
  fetch('/api/cases')
    .then(res => res.json())
    .then(data => setCases(data.cases))
}, [])

// Filter component
<div className="mb-4">
  <label className="block text-sm font-medium mb-2">Filter by Case</label>
  <Select value={selectedCase || "all"} onValueChange={setSelectedCase}>
    <SelectTrigger>
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
</div>
```

---

### 3. **Upload Form - Mandatory Case Name**

**File:** `/components/upload/*` (identify the upload form component)

**Current:** Case name is optional  
**Required:** Make case name a required field

**Implementation:**
```tsx
// Form validation
const formSchema = z.object({
  caseName: z.string()
    .min(1, "Case name is required")
    .max(100, "Case name must be less than 100 characters"),
  files: z.array(z.instanceof(File)).min(1, "At least one file required"),
  // ... other fields
})

// UI
<div className="space-y-2">
  <label htmlFor="caseName" className="text-sm font-medium">
    Case Name <span className="text-red-500">*</span>
  </label>
  <input
    id="caseName"
    name="caseName"
    type="text"
    required
    placeholder="e.g., Mumbai_Drug_Investigation_2024"
    className="w-full px-3 py-2 border rounded"
  />
  <p className="text-xs text-gray-500">
    Group related uploads under a case for better organization
  </p>
</div>
```

---

### 4. **Job History - Case Grouping**

**File:** Create or update job history component

**Features to Add:**
1. Case name column
2. Group jobs by case (collapsible sections)
3. Show parent-child relationships (tree view)
4. Case filter dropdown

**Example UI:**
```tsx
interface Job {
  id: string
  case_name: string
  parent_job_id?: string
  status: string
  total_files: number
  processed_files: number
  created_at: string
  // ... other fields
}

// Group jobs by case
const jobsByCase = groupBy(jobs, 'case_name')

// Render
{Object.entries(jobsByCase).map(([caseName, caseJobs]) => (
  <Collapsible key={caseName}>
    <CollapsibleTrigger className="flex items-center gap-2 font-semibold">
      <ChevronRight className="h-4 w-4" />
      Case: {caseName}
      <Badge>{caseJobs.length} jobs</Badge>
    </CollapsibleTrigger>
    <CollapsibleContent>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Job ID</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Files</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {caseJobs.map(job => (
            <TableRow key={job.id}>
              <TableCell className={job.parent_job_id ? "pl-8" : ""}>
                {job.parent_job_id && "↳ "}
                {job.id}
              </TableCell>
              <TableCell>
                <StatusBadge status={job.status} />
              </TableCell>
              <TableCell>{job.processed_files}/{job.total_files}</TableCell>
              <TableCell>{formatDate(job.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </CollapsibleContent>
  </Collapsible>
))}
```

---

### 5. **Real-Time Artifact Status Updates**

**File:** Create or update job detail/status component

**Features:**
1. Show per-artifact processing status
2. Display current processing stage
3. Show timing breakdown
4. Real-time updates via SSE or WebSocket

**Implementation:**

**Backend SSE Endpoint (already exists or add):**
```python
# backend/main.py
@app.get("/api/jobs/{job_id}/status/stream")
async def stream_job_status(job_id: str):
    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = f"job_status:{job_id}"
        pubsub.subscribe(channel)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Frontend:**
```tsx
import { useEffect, useState } from 'react'

interface ArtifactStatus {
  filename: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  current_stage?: string
  processing_stages?: Record<string, number>
  error_message?: string
}

export function JobStatusMonitor({ jobId }: { jobId: string }) {
  const [artifacts, setArtifacts] = useState<Record<string, ArtifactStatus>>({})

  useEffect(() => {
    // Connect to SSE stream
    const eventSource = new EventSource(`/api/jobs/${jobId}/status/stream`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'artifact_status') {
        setArtifacts(prev => ({
          ...prev,
          [data.filename]: {
            filename: data.filename,
            status: data.status,
            current_stage: data.current_stage,
            processing_stages: data.processing_stages,
            error_message: data.error_message
          }
        }))
      }
    }
    
    return () => eventSource.close()
  }, [jobId])

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Processing Status</h3>
      {Object.values(artifacts).map(artifact => (
        <Card key={artifact.filename}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">{artifact.filename}</CardTitle>
              <StatusBadge status={artifact.status} />
            </div>
          </CardHeader>
          <CardContent>
            {artifact.status === 'processing' && artifact.current_stage && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">
                    Stage: {artifact.current_stage.replace('_', ' ')}
                  </span>
                </div>
                
                {artifact.processing_stages && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-500">Timing Breakdown:</p>
                    {Object.entries(artifact.processing_stages).map(([stage, time]) => (
                      <div key={stage} className="flex justify-between text-xs">
                        <span className="capitalize">{stage.replace('_', ' ')}:</span>
                        <span className="font-mono">{time.toFixed(2)}s</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {artifact.status === 'completed' && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-sm">Completed successfully</span>
              </div>
            )}
            
            {artifact.status === 'failed' && artifact.error_message && (
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="h-4 w-4" />
                <span className="text-sm">{artifact.error_message}</span>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

---

### 6. **Results View - Case Context**

**File:** `/components/results/*`

**Features to Add:**
1. Display case name prominently
2. Show all artifacts in the same case
3. Highlight cross-document entity matches
4. Link to case overview

**Implementation:**
```tsx
export function ResultsView({ jobId }: { jobId: string }) {
  const { data: job } = useQuery(['job', jobId], () => 
    fetch(`/api/jobs/${jobId}`).then(r => r.json())
  )
  
  const { data: caseJobs } = useQuery(
    ['case', job?.case_name],
    () => fetch(`/api/cases/${job?.case_name}/jobs`).then(r => r.json()),
    { enabled: !!job?.case_name }
  )

  return (
    <div className="space-y-6">
      {/* Case Context */}
      {job?.case_name && (
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Case: {job.case_name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-sm">
                <span className="text-gray-600">Total uploads in case:</span>
                <span className="ml-2 font-semibold">{caseJobs?.jobs?.length || 0}</span>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/cases/${job.case_name}`}>
                  View All Case Files →
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Current Job Results */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Results for this Upload</h2>
        {/* ... existing results display ... */}
      </div>
    </div>
  )
}
```

---

### 7. **Status Badge Component**

**File:** `/components/common/status-badge.tsx` (create if doesn't exist)

```tsx
import { Badge } from "@/components/ui/badge"
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react"

interface StatusBadgeProps {
  status: 'queued' | 'processing' | 'completed' | 'failed'
  currentStage?: string
}

export function StatusBadge({ status, currentStage }: StatusBadgeProps) {
  const variants = {
    queued: { variant: "secondary", icon: Clock, text: "Queued" },
    processing: { variant: "default", icon: Loader2, text: currentStage || "Processing" },
    completed: { variant: "success", icon: CheckCircle2, text: "Completed" },
    failed: { variant: "destructive", icon: XCircle, text: "Failed" }
  }
  
  const config = variants[status] || variants.queued
  const Icon = config.icon
  
  return (
    <Badge variant={config.variant as any} className="flex items-center gap-1">
      <Icon className={`h-3 w-3 ${status === 'processing' ? 'animate-spin' : ''}`} />
      <span className="capitalize">{config.text.replace('_', ' ')}</span>
    </Badge>
  )
}
```

---

### 8. **Case Overview Page**

**File:** `/app/cases/[caseName]/page.tsx` (create new)

**Features:**
- List all jobs in the case
- Combined statistics
- Entity frequency across all documents
- Timeline visualization
- Export case report

**Implementation:**
```tsx
export default function CasePage({ params }: { params: { caseName: string } }) {
  const { data: caseData } = useQuery(['case', params.caseName], () =>
    fetch(`/api/cases/${params.caseName}/jobs`).then(r => r.json())
  )

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Case: {params.caseName}</h1>
        <Button>Export Case Report</Button>
      </div>
      
      {/* Case Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">Total Uploads</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{caseData?.jobs?.length || 0}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">Total Files</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {caseData?.jobs?.reduce((sum, job) => sum + job.total_files, 0) || 0}
            </p>
          </CardContent>
        </Card>
        
        {/* Add more stats */}
      </div>
      
      {/* Jobs Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {caseData?.jobs?.map(job => (
              <div key={job.id} className="flex items-center gap-4 p-3 border rounded">
                <div className="flex-1">
                  <p className="font-medium">{job.id}</p>
                  <p className="text-sm text-gray-500">
                    {job.total_files} files • {formatDate(job.created_at)}
                  </p>
                </div>
                <StatusBadge status={job.status} />
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/results?jobId=${job.id}`}>View</Link>
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## 📋 Testing Checklist

### Upload Flow
- [ ] Case name field is marked as required (red asterisk)
- [ ] Form validation prevents submission without case name
- [ ] Error message shown for empty case name
- [ ] Successful upload with valid case name

### Dashboard
- [ ] Components stacked vertically (not grid)
- [ ] Case filter dropdown loads all cases
- [ ] Selecting a case filters jobs correctly
- [ ] "All Cases" option shows all jobs

### Job History
- [ ] Jobs grouped by case name
- [ ] Case sections are collapsible
- [ ] Parent-child relationships indicated with indentation
- [ ] Case filter works correctly

### Real-Time Status
- [ ] Artifact status updates in real-time
- [ ] Current processing stage displayed
- [ ] Timing breakdown shown
- [ ] Final "completed" status only after graph processing
- [ ] Failed status shows error message

### Results View
- [ ] Case name displayed prominently
- [ ] Link to case overview page
- [ ] Shows related uploads in same case

---

## 🎨 UI/UX Recommendations

### Processing Stage Labels (User-Friendly)
```tsx
const stageLabels = {
  starting: "Initializing...",
  extraction: "Extracting text from document...",
  transcription: "Transcribing audio...",
  frame_extraction: "Extracting video frames...",
  video_analysis: "Analyzing video content...",
  translation: "Translating to English...",
  summarization: "Generating summary...",
  embeddings: "Creating searchable embeddings...",
  vectorization: "Creating searchable embeddings...",
  awaiting_graph: "Preparing for graph analysis...",
  graph_building: "Building knowledge graph...",
  completed: "Processing complete!"
}
```

### Color Coding
- **Queued**: Gray
- **Processing**: Blue (with spinner)
- **Awaiting Graph**: Orange (intermediate state)
- **Completed**: Green (checkmark)
- **Failed**: Red (error icon)

### Progress Indicator
```tsx
const stageOrder = [
  'extraction', 'translation', 'summarization', 
  'embeddings', 'graph_building', 'completed'
]

const currentIndex = stageOrder.indexOf(artifact.current_stage)
const progress = ((currentIndex + 1) / stageOrder.length) * 100

<Progress value={progress} className="h-2" />
```

---

## 🔌 API Endpoints Reference

### Jobs
- `GET /api/jobs` - List all jobs (with optional `case_name` filter)
- `GET /api/jobs/{job_id}` - Get job details
- `GET /api/jobs/{job_id}/status/stream` - SSE stream for real-time updates
- `POST /api/upload` - Upload files (requires `case_name`)

### Cases
- `GET /api/cases` - List all unique case names
- `GET /api/cases/{case_name}/jobs` - Get all jobs in a case
- `GET /api/cases/{case_name}/summary` - Case-wide summary (TODO)
- `GET /api/cases/{case_name}/entities` - Unique entities in case (TODO)

---

## 🚀 Implementation Priority

**Phase 1 (High Priority):**
1. ✅ Make case name mandatory in upload form
2. ✅ Add real-time artifact status updates
3. ✅ Stack dashboard components vertically

**Phase 2 (Medium Priority):**
4. Add case filter to dashboard
5. Update job history with case grouping
6. Display case context in results view

**Phase 3 (Low Priority - Enhancement):**
7. Create dedicated case overview page
8. Add case-wide analytics
9. Implement case timeline visualization

---

## 📞 Questions or Issues?

If you encounter any issues or have questions about implementation:
1. Check the backend implementation in processor files
2. Review the comprehensive guide: `ARTIFACT_STATUS_AND_CASE_WORKFLOW.md`
3. Test API endpoints directly to understand the data structure
4. Refer to existing components for patterns (badges, cards, etc.)

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15
