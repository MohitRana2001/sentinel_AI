# Redis Document Queue Debugging Guide

## Issue Description
Documents are getting summarized and passed to the graph queue, but the Redis document queue appears to remain empty.

## Enhanced Logging

We've added comprehensive logging throughout the system to track message flow:

### 1. Upload Endpoint (main.py)
- Shows when files are pushed to queues
- Displays queue length after each push
- Example output:
  ```
  📤 Pushed to document_queue: file.pdf (queue length: 1)
  ✅ Job xyz created: 1 file(s) queued for processing
  ```

### 2. Document Processor (document_processor_service.py)
- Shows startup configuration
- Logs when messages are received
- Logs warnings for unknown actions
- Example output:
  ```
  ================================================================================
  Starting Document Processor Service...
  ================================================================================
  ✓ Using Redis Queue for true parallel processing
  ✓ Queue name: document_queue
  ✓ Redis host: localhost:6379
  ================================================================================

  👂 Listening for messages on queue: document_queue

  📥 Received message from queue: action=process_file, job_id=xyz
  Document Processor received file: file.pdf (job: xyz)
  ```

### 3. Graph Processor (graph_processor_service.py)
- Shows when it receives messages from document processor
- Confirms the queue is working
- Example output:
  ```
  📊 Graph Processor received job for document: 123
     └─ Job ID: xyz
     └─ Username: user@example.com
     └─ Time: 12:30:45
  ```

### 4. Redis Pub/Sub Module (redis_pubsub.py)
- Logs every push and pop operation
- Shows queue lengths
- Example output:
  ```
  🔵 Redis LPUSH: queue=document_queue, new_length=1
  🟢 Redis BRPOP: queue=document_queue, received message
  ```

## Monitoring Tool

Run the queue monitor to observe queues in real-time:

```bash
cd backend
python monitor_queues.py
```

This will show:
- Current length of all queues (document, audio, video, graph)
- Number of subscribers to legacy channels (should be 0)
- Updates every 2 seconds
- Press Ctrl+C to stop

## Expected Behavior

### Normal Operation
1. **Upload**: File is uploaded, message pushed to `document_queue`
   - Log: `📤 Pushed to document_queue`
   - Log: `🔵 Redis LPUSH: queue=document_queue, new_length=N`

2. **Document Processor**: Immediately consumes message
   - Log: `🟢 Redis BRPOP: queue=document_queue, received message`
   - Log: `📥 Received message from queue`
   - Queue length drops to N-1 (or 0 if only one message)

3. **Processing**: Document is OCR'd, translated, summarized
   - Various processing logs...

4. **Graph Queue**: Document processor pushes to `graph_queue`
   - Log: `🔵 Redis LPUSH: queue=graph_queue, new_length=M`

5. **Graph Processor**: Consumes from graph queue
   - Log: `🟢 Redis BRPOP: queue=graph_queue, received message`
   - Log: `📊 Graph Processor received job`

### Why Document Queue Appears Empty

**This is NORMAL BEHAVIOR!**

Redis queues are designed to be fast. When a worker is listening (using BRPOP), it immediately receives messages as they arrive. The queue appears empty because:

1. **Producer** (upload endpoint) pushes to left of queue (LPUSH)
2. **Consumer** (document processor) blocks waiting for messages (BRPOP)
3. **Redis** immediately delivers message to waiting consumer
4. Queue never accumulates messages (except during high load)

### How to Verify It's Working

1. **Check logs** for the full flow:
   - Upload: `📤 Pushed to document_queue`
   - Redis: `🔵 Redis LPUSH` followed immediately by `🟢 Redis BRPOP`
   - Processor: `📥 Received message from queue`

2. **Monitor queue length** during upload:
   - Run `monitor_queues.py` in one terminal
   - Upload a file in another terminal
   - You should see queue length briefly increase then decrease

3. **Check document processing**:
   - Documents get summarized ✓
   - Summaries appear in storage ✓
   - Messages arrive in graph queue ✓
   - All of this confirms document processor IS working

## Troubleshooting

### If document queue is NOT working:

1. **Document processor not running**
   - Check: `docker ps` or process list
   - Should see: `sentinel-document-processor` container
   - Logs should show: "Starting Document Processor Service..."

2. **Wrong queue name**
   - Check config: Queue should be `document_queue` NOT `document_processor`
   - Old channel name: `document_processor` (deprecated)
   - New queue name: `document_queue` (current)

3. **Redis connection issue**
   - Check Redis is running: `redis-cli ping` should return `PONG`
   - Check connection in logs: Should show Redis host/port at startup

4. **Messages going to wrong queue**
   - Check upload logs: Should say "Pushed to document_queue"
   - NOT "Pushed to document_processor" (that's the old channel)

### If messages are being skipped:

Check for this warning in logs:
```
⚠️  Unknown action 'XXX' - ignoring message
```

This means the message format is incorrect. Should be:
```json
{
  "job_id": "...",
  "gcs_path": "...",
  "filename": "...",
  "action": "process_file"
}
```

## Key Files Modified

1. `backend/main.py` - Upload endpoint (lines 702-720)
2. `backend/redis_pubsub.py` - Push/pop logging (lines 45-48, 102-105)
3. `backend/processors/document_processor_service.py` - Message handling (lines 29-40, 331-346)
4. `backend/processors/graph_processor_service.py` - Graph message handling (lines 41-62, 377-389)
5. `backend/monitor_queues.py` - NEW monitoring tool

## Testing

To test the full flow:

1. Start all services:
   ```bash
   docker-compose up -d
   ```

2. Watch logs in real-time:
   ```bash
   # Terminal 1: Document processor logs
   docker logs -f sentinel-document-processor

   # Terminal 2: Graph processor logs  
   docker logs -f sentinel-graph-processor

   # Terminal 3: Backend logs
   docker logs -f sentinel-backend

   # Terminal 4: Monitor queues
   docker exec -it sentinel-document-processor python monitor_queues.py
   ```

3. Upload a test file through the API or UI

4. Watch the logs flow through all stages

## Conclusion

The queue IS working correctly if:
- ✅ Upload logs show messages being pushed
- ✅ Document processor logs show messages being received
- ✅ Documents get summarized
- ✅ Graph processor receives messages
- ✅ Queue appears empty (because messages are consumed immediately)

The queue is NOT working if:
- ❌ Upload shows push but processor never receives
- ❌ Documents don't get summarized
- ❌ Queue length keeps growing without being consumed
