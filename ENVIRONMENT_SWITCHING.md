# Environment Switching - Quick Reference

This document provides a quick reference for switching between local development and production environments.

## 🔑 Key Environment Variables

Only **TWO** environment variables control the entire environment mode:

```bash
# LOCAL DEVELOPMENT MODE
USE_GEMINI_FOR_DEV=true      # Use Google Gemini API (requires GEMINI_API_KEY)
USE_SQLITE_FOR_DEV=true      # Use SQLite database (no setup needed)

# PRODUCTION MODE
USE_GEMINI_FOR_DEV=false     # Use Ollama with Gemma models (self-hosted)
USE_SQLITE_FOR_DEV=false     # Use AlloyDB/PostgreSQL (requires setup)
```

## 📋 What Each Flag Controls

### `USE_GEMINI_FOR_DEV=true`
When enabled:
- ✅ Uses Google Gemini API for all LLM operations
- ✅ No need to run Ollama servers
- ✅ Works with just a GEMINI_API_KEY
- ✅ Faster setup for development
- 🎯 **Use for:** Local development, testing, prototyping

**Affects:**
- Document summarization
- Text translation
- Chat/RAG responses
- Audio transcription
- Graph entity extraction

**Required:**
- `GEMINI_API_KEY` in `.env` file
- Internet connection

### `USE_GEMINI_FOR_DEV=false`
When disabled:
- 🚀 Uses Ollama with Gemma models
- 🚀 Self-hosted, no API costs
- 🚀 Better for production privacy
- 🚀 Requires GPU for optimal performance
- 🎯 **Use for:** Production, self-hosted deployments

**Requires:**
- Ollama server running on ports: 11434, 11435, 11436, 11437
- Gemma models downloaded: `gemma3:1b`, `gemma3:4b`, `gemma3:12b`, `embeddinggemma`

---

### `USE_SQLITE_FOR_DEV=true`
When enabled:
- ✅ Uses SQLite database (single file)
- ✅ No database server setup needed
- ✅ Perfect for local development
- ✅ File: `backend/sentinel_dev.db`
- 🎯 **Use for:** Local development, testing

**Pros:**
- Zero configuration
- Portable (single file)
- Fast for development
- No separate server needed

**Cons:**
- Not suitable for production
- No concurrent write support
- Limited scalability

### `USE_SQLITE_FOR_DEV=false`
When disabled:
- 🚀 Uses AlloyDB/PostgreSQL
- 🚀 Production-grade database
- 🚀 Supports pgvector extension
- 🚀 Horizontal scalability
- 🎯 **Use for:** Production deployments

**Requires:**
- PostgreSQL/AlloyDB server
- `ALLOYDB_HOST`, `ALLOYDB_PASSWORD`, etc. configured

---

## 🎬 Quick Start Commands

### Local Development Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env file (set these two lines)
USE_GEMINI_FOR_DEV=true
USE_SQLITE_FOR_DEV=true
GEMINI_API_KEY=your-api-key-here

# 3. Install dependencies
cd backend && pip install -r requirements.txt
cd .. && npm install

# 4. Start dependencies (Redis, Neo4j)
docker-compose up -d redis neo4j

# 5. Run backend
cd backend && python main.py

# 6. Run frontend (in new terminal)
npm run dev
```

### Production Setup

```bash
# 1. Configure production .env
USE_GEMINI_FOR_DEV=false
USE_SQLITE_FOR_DEV=false

# 2. Configure AlloyDB
ALLOYDB_HOST=your-alloydb-ip
ALLOYDB_PASSWORD=your-password
ALLOYDB_DATABASE=sentinel_db

# 3. Configure GCS
GCS_BUCKET_NAME=your-bucket
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/path/to/gcs-key.json

# 4. Set up Ollama (on your server)
ollama pull gemma3:1b
ollama pull gemma3:4b
ollama pull gemma3:12b
ollama pull embeddinggemma

# 5. Run Ollama instances
OLLAMA_HOST=0.0.0.0:11434 ollama serve &  # Summary
OLLAMA_HOST=0.0.0.0:11435 ollama serve &  # Graph
OLLAMA_HOST=0.0.0.0:11436 ollama serve &  # Chat
OLLAMA_HOST=0.0.0.0:11437 ollama serve &  # Multimodal

# 6. Deploy with Docker or Kubernetes
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔄 Switching Between Environments

### Method 1: Manual Edit

Edit your `.env` file:

```bash
# Switch to local
USE_GEMINI_FOR_DEV=true
USE_SQLITE_FOR_DEV=true

# Switch to production
USE_GEMINI_FOR_DEV=false
USE_SQLITE_FOR_DEV=false
```

Then restart your services.

### Method 2: Using Script

Create `switch-env.sh`:

```bash
#!/bin/bash
if [ "$1" == "local" ]; then
    sed -i.bak 's/USE_GEMINI_FOR_DEV=false/USE_GEMINI_FOR_DEV=true/g' .env
    sed -i.bak 's/USE_SQLITE_FOR_DEV=false/USE_SQLITE_FOR_DEV=true/g' .env
    echo "✅ Switched to LOCAL mode"
elif [ "$1" == "prod" ]; then
    sed -i.bak 's/USE_GEMINI_FOR_DEV=true/USE_GEMINI_FOR_DEV=false/g' .env
    sed -i.bak 's/USE_SQLITE_FOR_DEV=true/USE_SQLITE_FOR_DEV=false/g' .env
    echo "✅ Switched to PRODUCTION mode"
else
    echo "Usage: ./switch-env.sh [local|prod]"
fi
```

```bash
chmod +x switch-env.sh
./switch-env.sh local   # Switch to local
./switch-env.sh prod    # Switch to production
```

### Method 3: Separate Environment Files

Create multiple env files:

```bash
# .env.local - Local development
cp .env.example .env.local
# Edit: Set USE_GEMINI_FOR_DEV=true, USE_SQLITE_FOR_DEV=true

# .env.production - Production
cp .env.example .env.production
# Edit: Set USE_GEMINI_FOR_DEV=false, USE_SQLITE_FOR_DEV=false

# Switch by copying
cp .env.local .env      # Use local
cp .env.production .env # Use production
```

---

## 🧪 Testing Your Configuration

### Verify Environment Mode

Run this Python script to check which mode you're in:

```python
# check_env.py
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("ENVIRONMENT CONFIGURATION CHECK")
print("=" * 50)

use_gemini = os.getenv("USE_GEMINI_FOR_DEV", "false").lower() == "true"
use_sqlite = os.getenv("USE_SQLITE_FOR_DEV", "false").lower() == "true"

if use_gemini and use_sqlite:
    print("✅ MODE: LOCAL DEVELOPMENT")
    print("   - Using Gemini API")
    print("   - Using SQLite database")
    print("   - Using local file storage")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and gemini_key != "your-gemini-api-key-here":
        print("   ✅ Gemini API key configured")
    else:
        print("   ❌ Gemini API key NOT configured")
        
elif not use_gemini and not use_sqlite:
    print("✅ MODE: PRODUCTION")
    print("   - Using Ollama/Gemma models")
    print("   - Using AlloyDB/PostgreSQL")
    print("   - Using Google Cloud Storage")
    
    # Check required configs
    alloydb_host = os.getenv("ALLOYDB_HOST", "localhost")
    gcs_bucket = os.getenv("GCS_BUCKET_NAME", "")
    
    print(f"   - AlloyDB Host: {alloydb_host}")
    print(f"   - GCS Bucket: {gcs_bucket or 'NOT CONFIGURED'}")
    
else:
    print("⚠️  WARNING: MIXED CONFIGURATION")
    print(f"   - USE_GEMINI_FOR_DEV: {use_gemini}")
    print(f"   - USE_SQLITE_FOR_DEV: {use_sqlite}")
    print("   - This is not recommended. Set both to true or both to false.")

print("=" * 50)
```

Run:
```bash
cd backend
python check_env.py
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get configuration
curl http://localhost:8000/api/v1/config

# Check what's actually being used
curl http://localhost:8000/api/v1/health | jq .
```

---

## 📊 Environment Comparison

| Feature | Local Dev | Production |
|---------|-----------|------------|
| **LLM** | Gemini API | Ollama/Gemma |
| **Database** | SQLite | AlloyDB |
| **Storage** | Local Files | GCS |
| **Setup Time** | ~5 minutes | ~1 hour |
| **Cost** | API costs | Infrastructure costs |
| **Privacy** | Data sent to Google | Fully self-hosted |
| **Performance** | Fast (cloud) | Depends on hardware |
| **Scalability** | Limited | Highly scalable |

---

## 🔐 Security Considerations

### Local Development
- ⚠️ Data is sent to Google Gemini API
- ⚠️ Use only for non-sensitive data
- ⚠️ Never commit `.env` with real API keys
- ✅ Perfect for testing and development

### Production
- ✅ All data stays in your infrastructure
- ✅ Full control over data processing
- ✅ GDPR/HIPAA compliant (with proper setup)
- ⚠️ Requires proper security hardening

---

## 🐛 Common Issues

### Issue: "Gemini API key not configured"
**Solution:**
```bash
# Make sure .env has:
USE_GEMINI_FOR_DEV=true
GEMINI_API_KEY=your-actual-api-key

# Get API key from: https://makersuite.google.com/app/apikey
```

### Issue: "Database connection failed"
**Solution:**
```bash
# For local dev, use SQLite:
USE_SQLITE_FOR_DEV=true

# For production, verify AlloyDB settings:
USE_SQLITE_FOR_DEV=false
ALLOYDB_HOST=correct-ip-address
ALLOYDB_PASSWORD=correct-password
```

### Issue: "Ollama connection refused"
**Solution:**
```bash
# Make sure USE_GEMINI_FOR_DEV=true for local dev
# Or ensure Ollama is running:
curl http://localhost:11434/api/tags

# Start Ollama if not running:
ollama serve
```

### Issue: "GCS permission denied"
**Solution:**
```bash
# For local dev, system will use local storage automatically
# No GCS credentials needed if GCS_CREDENTIALS_PATH is not found

# For production, verify:
# 1. Service account has Storage Object Admin role
# 2. Credentials file exists at GCS_CREDENTIALS_PATH
# 3. GCS_BUCKET_NAME is correct
```

---

## 📝 Configuration Files Quick Reference

### `.env` - Main configuration file
- Copy from `.env.example`
- Contains all environment variables
- **Never commit to git**

### `.env.example` - Template file
- Committed to git
- Safe to share
- Contains example values

### `backend/config.py` - Configuration loader
- Reads environment variables
- Applies defaults
- Controls environment switching logic

### `docker-compose.yml` - Local Docker setup
- Uses environment variables from `.env`
- Includes Redis, Neo4j, AlloyDB (local), Ollama

### `docker-compose.prod.yml` - Production Docker setup
- Production-optimized
- Uses external services (AlloyDB, GCS)

---

## 🎓 Best Practices

1. **Never mix modes**: Always set both flags the same way
   ```bash
   # ✅ Good
   USE_GEMINI_FOR_DEV=true
   USE_SQLITE_FOR_DEV=true
   
   # ✅ Good
   USE_GEMINI_FOR_DEV=false
   USE_SQLITE_FOR_DEV=false
   
   # ❌ Bad (mixed)
   USE_GEMINI_FOR_DEV=true
   USE_SQLITE_FOR_DEV=false
   ```

2. **Keep separate .env files**:
   ```bash
   .env.local        # Local development
   .env.staging      # Staging environment
   .env.production   # Production
   ```

3. **Use environment-specific secrets**:
   - Different API keys per environment
   - Different database passwords
   - Different JWT secrets

4. **Test before deploying**:
   ```bash
   # Test locally first
   ./switch-env.sh local
   python backend/main.py
   
   # Then test production config
   ./switch-env.sh prod
   python backend/main.py
   ```

---

## 📞 Need Help?

1. Check the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed setup
2. Verify `.env` configuration
3. Run `python check_env.py` to verify settings
4. Check logs for specific errors
5. Ensure all required services are running

---

**Remember: Just two flags control everything! 🎯**

```bash
USE_GEMINI_FOR_DEV=true/false
USE_SQLITE_FOR_DEV=true/false
```

That's it! 🚀

