#!/bin/bash

# Sentinel AI - Quick Start Script
# This script helps you start and test the application locally

set -e

echo "🚀 Sentinel AI - Quick Start"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
    else
        echo "Creating default .env file..."
        cat > .env << EOF
# Upload Limits
MAX_UPLOAD_FILES=10
MAX_FILE_SIZE_MB=4
ALLOWED_EXTENSIONS=.pdf,.docx,.txt,.mp3,.wav,.mp4,.avi,.mov

# GCS Configuration (Optional for local dev)
GCS_BUCKET_NAME=sentinel-local
GCS_PROJECT_ID=local-dev
EOF
        echo -e "${GREEN}✅ Created default .env file${NC}"
    fi
fi

echo ""
echo "📦 Starting Docker containers..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

echo ""
echo -e "${BLUE}📥 Pulling LLM models (this may take a few minutes)...${NC}"
echo ""

# Pull models
echo "Pulling Summary LLM (gemma2:2b)..."
docker exec sentinel-summary-llm ollama pull gemma2:2b || true

echo "Pulling Graph LLM (gemma2:2b)..."
docker exec sentinel-graph-llm ollama pull gemma2:2b || true

echo "Pulling Chat LLM (gemma2:2b)..."
docker exec sentinel-chat-llm ollama pull gemma2:2b || true

echo "Pulling Embedding model (nomic-embed-text)..."
docker exec sentinel-summary-llm ollama pull nomic-embed-text || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Sentinel AI is ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "🌐 Access the application:"
echo ""
echo "  Frontend:     http://localhost:3000"
echo "  Backend API:  http://localhost:8000/api/v1/docs"
echo "  Neo4j:        http://localhost:7474"
echo "                (user: neo4j, password: password)"
echo ""
echo "📊 View logs:"
echo "  docker-compose logs -f backend"
echo "  docker-compose logs -f document-processor"
echo "  docker-compose logs -f frontend"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose down"
echo ""
echo "📚 For more information, see TESTING_GUIDE.md"
echo ""

