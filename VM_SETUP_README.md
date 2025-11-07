# VM Integration Guide for Sentinel AI

## Overview

This guide documents the integration of **Document Processor** and **Graph Processor** services into separate Virtual Machines (VMs) as part of the Sentinel AI distributed architecture. The services are decoupled from the main application and communicate via Redis queues, enabling independent scaling and fault tolerance.

## 📚 Documentation Structure

This repository contains comprehensive documentation for setting up and managing the VM-based architecture:

### Core Setup Guides

1. **[QUICKSTART_VM_SETUP.md](./QUICKSTART_VM_SETUP.md)** ⚡
   - **Purpose**: Get both VMs running quickly (~1 hour)
   - **Best for**: First-time setup, rapid deployment
   - **Contains**: Essential commands, minimal explanations, quick testing

2. **[VM_SETUP_DOCUMENT_PROCESSOR.md](./VM_SETUP_DOCUMENT_PROCESSOR.md)** 📄
   - **Purpose**: Complete Document Processor VM setup with detailed explanations
   - **Best for**: Understanding how document processing works
   - **Contains**: 
     - System requirements and prerequisites
     - Step-by-step installation (dependencies, Python, Tesseract OCR)
     - Configuration explanations for Redis, AlloyDB, GCS, LLMs
     - Connectivity testing procedures
     - Systemd service setup for auto-start
     - Scaling strategies (multiple workers)
     - Performance tuning guidelines
     - Comprehensive troubleshooting

3. **[VM_SETUP_GRAPH_PROCESSOR.md](./VM_SETUP_GRAPH_PROCESSOR.md)** 🕸️
   - **Purpose**: Complete Graph Processor VM setup with detailed explanations
   - **Best for**: Understanding how knowledge graph building works
   - **Contains**:
     - System requirements (higher RAM for LLM processing)
     - Neo4j integration and setup
     - LLM configuration for entity extraction
     - Entity resolution across documents
     - Cross-document graph linking
     - Advanced graph query examples
     - Memory management strategies
     - Detailed troubleshooting

### Architecture Documentation

4. **[VM_INTEGRATION_ARCHITECTURE.md](./VM_INTEGRATION_ARCHITECTURE.md)** 🏗️
   - **Purpose**: Understand the complete distributed system design
   - **Best for**: Architecture review, system design discussions
   - **Contains**:
     - Complete system architecture diagrams
     - Component responsibilities and interactions
     - Data flow through entire pipeline
     - Network requirements and firewall rules
     - Scaling strategies (horizontal and vertical)
     - Fault tolerance and reliability patterns
     - Monitoring and observability guidelines
     - Cost optimization strategies
     - Security considerations
     - Deployment checklist

### Configuration Templates

5. **[config-templates/document-processor.env.template](./config-templates/document-processor.env.template)** ⚙️
   - Environment variables for Document Processor VM
   - Includes comments explaining each setting
   - Copy to `.env` and fill in your values

6. **[config-templates/graph-processor.env.template](./config-templates/graph-processor.env.template)** ⚙️
   - Environment variables for Graph Processor VM
   - Neo4j and LLM-specific configurations
   - Copy to `.env` and fill in your values

## 🎯 Quick Navigation

### I'm new to this project
→ Start with [VM_INTEGRATION_ARCHITECTURE.md](./VM_INTEGRATION_ARCHITECTURE.md) to understand the system
→ Then follow [QUICKSTART_VM_SETUP.md](./QUICKSTART_VM_SETUP.md) to set up your VMs

### I need to set up Document Processor
→ Use [QUICKSTART_VM_SETUP.md](./QUICKSTART_VM_SETUP.md) for quick setup
→ Or [VM_SETUP_DOCUMENT_PROCESSOR.md](./VM_SETUP_DOCUMENT_PROCESSOR.md) for detailed walkthrough

### I need to set up Graph Processor
→ Use [QUICKSTART_VM_SETUP.md](./QUICKSTART_VM_SETUP.md) for quick setup
→ Or [VM_SETUP_GRAPH_PROCESSOR.md](./VM_SETUP_GRAPH_PROCESSOR.md) for detailed walkthrough

### I'm troubleshooting an issue
→ Check troubleshooting sections in the specific VM guide
→ Review connectivity tests in the setup guides
→ Check [VM_INTEGRATION_ARCHITECTURE.md](./VM_INTEGRATION_ARCHITECTURE.md) for monitoring strategies

### I need to scale the system
→ See scaling sections in VM-specific guides
→ Review [VM_INTEGRATION_ARCHITECTURE.md](./VM_INTEGRATION_ARCHITECTURE.md) for scaling strategies

## 🏗️ Architecture Overview

```
┌──────────────┐     ┌─────────┐     ┌─────────────────────┐
│  Main App    │────▶│  Redis  │◀────│ Document Processor  │
│  (FastAPI)   │     │ (Queue) │     │      VM             │
└──────────────┘     └─────────┘     └─────────────────────┘
       │                                        │
       ▼                                        ▼
┌──────────────────┐                 ┌──────────────────────┐
│   AlloyDB        │                 │  Cloud Storage       │
│  (PostgreSQL)    │                 │  (GCS/Network)       │
└──────────────────┘                 └──────────────────────┘
       ▲                                        │
       │                                        │
       │              ┌─────────────────────┐   │
       │              │  Graph Processor    │◀──┘
       │              │      VM             │
       │              └─────────────────────┘
       │                        │
       │                        ▼
       │              ┌─────────────────────┐
       └──────────────│      Neo4j          │
                      │  (Graph Database)   │
                      └─────────────────────┘
```

### What Each Component Does

**Main Application (FastAPI)**:
- Handles user uploads and creates jobs
- Stores files in cloud storage
- Pushes work to Redis queues
- Serves query/chat interface
- Provides graph visualization API

**Document Processor VM**:
- Pulls files from `document_queue`
- Extracts text (OCR for PDFs)
- Detects language and translates
- Generates summaries using LLM
- Creates embeddings for search
- Stores chunks in database
- Queues documents for graph processing

**Graph Processor VM**:
- Pulls from `graph_queue`
- Extracts entities using LLM
- Identifies relationships
- Builds knowledge graph in Neo4j
- Performs entity resolution
- Marks jobs as complete

**Redis**:
- Coordinates work distribution
- Ensures fault tolerance
- Enables scaling

**AlloyDB (PostgreSQL + pgvector)**:
- Stores all application data
- Provides vector search
- Fast metadata queries

**Neo4j**:
- Stores knowledge graph
- Enables complex graph queries
- Powers visualization

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:

1. **Infrastructure**:
   - [ ] 2 Ubuntu 22.04 VMs provisioned
   - [ ] Redis server running
   - [ ] PostgreSQL/AlloyDB server running
   - [ ] Neo4j server running
   - [ ] Ollama LLM servers with models loaded
   - [ ] GCS bucket or network storage

2. **Access**:
   - [ ] SSH access to both VMs
   - [ ] Network connectivity between all components
   - [ ] Service credentials (Redis, DB, Neo4j, GCS)

3. **Knowledge**:
   - Basic Linux system administration
   - Understanding of systemd services
   - Familiarity with environment variables

### Step-by-Step Setup

**Option 1: Quick Setup (~1 hour)**
1. Follow [QUICKSTART_VM_SETUP.md](./QUICKSTART_VM_SETUP.md)
2. Copy configuration templates and fill in your values
3. Start services and verify

**Option 2: Detailed Setup (2-3 hours, deeper understanding)**
1. Read [VM_INTEGRATION_ARCHITECTURE.md](./VM_INTEGRATION_ARCHITECTURE.md)
2. Follow [VM_SETUP_DOCUMENT_PROCESSOR.md](./VM_SETUP_DOCUMENT_PROCESSOR.md)
3. Follow [VM_SETUP_GRAPH_PROCESSOR.md](./VM_SETUP_GRAPH_PROCESSOR.md)
4. Test end-to-end as described in guides

## 📊 System Requirements

### Document Processor VM
- **CPU**: 4-8 cores
- **RAM**: 8-16 GB
- **Disk**: 50 GB
- **Network**: Access to Redis, AlloyDB, Storage, LLMs

### Graph Processor VM
- **CPU**: 4-8 cores
- **RAM**: 16-32 GB (LLM needs more memory)
- **Disk**: 50 GB
- **Network**: Access to Redis, AlloyDB, Neo4j, Storage, LLMs

### Supporting Services
- **Redis**: 2-4 cores, 4-8 GB RAM
- **AlloyDB**: Based on data volume and query load
- **Neo4j**: 4 cores, 8-16 GB RAM
- **Ollama LLMs**: 8+ cores, 16-32 GB RAM (or GPU)

## 🔧 Key Features

### Why Separate VMs?

1. **Independent Scaling**: Scale document and graph processing independently
2. **Fault Isolation**: One service failure doesn't affect others
3. **Resource Optimization**: Different resource profiles (CPU vs memory)
4. **Easier Maintenance**: Update/restart services independently
5. **Clear Boundaries**: Well-defined responsibilities per component

### Queue-Based Architecture

- **Reliable**: Messages persist until acknowledged
- **Scalable**: Add workers without code changes
- **Observable**: Monitor queue depth in real-time
- **Fault-Tolerant**: Failed workers don't lose messages

### No Docker/Containers

This architecture **intentionally avoids Docker and Docker Compose** as requested:

- Direct VM deployment for full control
- Systemd for service management
- Traditional Linux admin workflows
- Easier integration with existing VM infrastructure

## 🔍 Monitoring and Maintenance

### Monitor Queue Depths

```bash
# Document queue
redis-cli -h <REDIS_IP> LLEN document_queue

# Graph queue
redis-cli -h <REDIS_IP> LLEN graph_queue
```

### Check Service Status

```bash
# Document processor
sudo systemctl status document-processor.service

# Graph processor
sudo systemctl status graph-processor.service
```

### View Logs

```bash
# Document processor
tail -f /var/log/sentinel_ai/document-processor.log

# Graph processor
tail -f /var/log/sentinel_ai/graph-processor.log
```

### Resource Usage

```bash
# CPU and memory
htop

# Disk space
df -h

# Network
iftop
```

## 🛠️ Scaling

### Add More Document Processor Workers

```bash
# On Document Processor VM
sudo systemctl start document-processor@{1..3}.service
```

Each worker independently pulls from the queue.

### Add More Graph Processor Workers

```bash
# On Graph Processor VM
sudo systemctl start graph-processor@{1..2}.service
```

Note: 2-4 workers optimal due to LLM bottleneck.

### Add More VMs

1. Provision new VM
2. Follow same setup guide
3. Start services
4. Workers automatically share queue load

## 🔒 Security

### Network Security
- Use private network (VPC) for internal communication
- Firewall rules to restrict access
- Only Main App exposed to internet

### Credentials
- Store in `.env` files with restrictive permissions (chmod 600)
- Never commit secrets to Git
- Rotate passwords regularly
- Use separate credentials per environment

### Data Encryption
- Enable encryption at rest for databases
- Use TLS for Redis in production
- SSL/TLS for Neo4j connections

## 📈 Performance

### Typical Processing Times

- **Small document** (1-2 pages): 10-20 seconds
- **Medium document** (10-20 pages): 30-60 seconds
- **Large document** (50+ pages): 2-5 minutes

### Bottlenecks

1. **LLM inference** (both document and graph)
2. **OCR processing** (for image-based PDFs)
3. **Network latency** (between services)

### Optimization Strategies

- Use GPU for LLM inference (3-5x speedup)
- Run multiple workers
- Optimize network connectivity
- Tune chunk sizes and overlaps

## 🆘 Troubleshooting

### Service Won't Start

1. Check service status: `systemctl status <service>`
2. View logs: `journalctl -u <service> -n 100`
3. Verify configuration: Check `.env` file
4. Test connectivity: Redis, DB, Neo4j, LLM

### Queue Not Moving

1. Check workers are running: `systemctl status`
2. Check queue depth: `redis-cli LLEN <queue>`
3. View worker logs for errors
4. Verify LLM is responding

### Out of Memory

1. Check memory usage: `free -h`
2. Reduce number of workers
3. Increase VM RAM
4. Add swap space (temporary fix)

### Connection Errors

1. Test connectivity: `ping`, `telnet`, `curl`
2. Check firewall rules: `sudo ufw status`
3. Verify credentials in `.env`
4. Check service is listening on expected port

## 📝 Change Log

### Version 1.0 (Current)
- Initial VM integration documentation
- Document Processor setup guide
- Graph Processor setup guide
- Architecture overview
- Configuration templates
- Quick start guide

## 🤝 Contributing

To improve this documentation:

1. Test the setup procedures
2. Note any issues or unclear sections
3. Suggest improvements
4. Add troubleshooting tips based on your experience

## 📞 Support

For issues:

1. **Check documentation**: Review the relevant setup guide
2. **Check logs**: View service logs for specific errors
3. **Test connectivity**: Verify all services are accessible
4. **Search issues**: Check if others have reported similar problems
5. **Create issue**: Provide logs, configuration (redact secrets), and steps to reproduce

## 📜 License

This documentation is part of the Sentinel AI project.

---

**Last Updated**: 2025-01-07

**Documentation Version**: 1.0

**Maintained By**: Sentinel AI Team

---

## Quick Links

- [Quick Start Guide](./QUICKSTART_VM_SETUP.md)
- [Document Processor Setup](./VM_SETUP_DOCUMENT_PROCESSOR.md)
- [Graph Processor Setup](./VM_SETUP_GRAPH_PROCESSOR.md)
- [Architecture Overview](./VM_INTEGRATION_ARCHITECTURE.md)
- [Document Processor Config](./config-templates/document-processor.env.template)
- [Graph Processor Config](./config-templates/graph-processor.env.template)
