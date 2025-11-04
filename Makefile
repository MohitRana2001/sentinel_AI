# Sentinel AI - Makefile
# Convenient commands for development and deployment

.PHONY: help
help: ## Show this help message
	@echo "Sentinel AI - Available Commands"
	@echo "=================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment Management
.PHONY: check-env
check-env: ## Check environment configuration
	@python3 check_env.py

.PHONY: switch-local
switch-local: ## Switch to local development mode
	@echo "🔄 Switching to LOCAL development mode..."
	@sed -i.bak 's/USE_GEMINI_FOR_DEV=false/USE_GEMINI_FOR_DEV=true/g' .env || true
	@sed -i.bak 's/USE_SQLITE_FOR_DEV=false/USE_SQLITE_FOR_DEV=true/g' .env || true
	@echo "✅ Switched to local mode (Gemini + SQLite)"
	@python3 check_env.py

.PHONY: switch-prod
switch-prod: ## Switch to production mode
	@echo "🔄 Switching to PRODUCTION mode..."
	@sed -i.bak 's/USE_GEMINI_FOR_DEV=true/USE_GEMINI_FOR_DEV=false/g' .env || true
	@sed -i.bak 's/USE_SQLITE_FOR_DEV=true/USE_SQLITE_FOR_DEV=false/g' .env || true
	@echo "✅ Switched to production mode (Ollama + AlloyDB)"
	@python3 check_env.py

.PHONY: create-env
create-env: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from .env.example"; \
		echo "⚠️  Please edit .env and add your credentials"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# Local Development
.PHONY: install
install: ## Install all dependencies (backend + frontend)
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	npm install
	@echo "✅ All dependencies installed"

.PHONY: dev-setup
dev-setup: create-env install ## Complete local development setup
	@echo "🚀 Starting development services (Redis, Neo4j)..."
	docker-compose up -d redis neo4j
	@echo "✅ Development setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env and add your GEMINI_API_KEY"
	@echo "2. Run: make dev"

.PHONY: dev
dev: ## Start local development (backend + frontend)
	@echo "🚀 Starting Sentinel AI in development mode..."
	@echo "Starting backend..."
	@cd backend && python main.py &
	@sleep 3
	@echo "Starting frontend..."
	@npm run dev

.PHONY: dev-backend
dev-backend: ## Start only backend (local development)
	@echo "🚀 Starting backend..."
	cd backend && python main.py

.PHONY: dev-frontend
dev-frontend: ## Start only frontend (local development)
	@echo "🚀 Starting frontend..."
	npm run dev

.PHONY: dev-processors
dev-processors: ## Start processor services (local development)
	@echo "🚀 Starting processor services..."
	@cd backend && python processors/document_processor_service.py &
	@cd backend && python processors/audio_video_processor_service.py &
	@cd backend && python processors/graph_processor_service.py &
	@echo "✅ Processor services started in background"

# Docker Commands
.PHONY: docker-dev
docker-dev: ## Start all services with Docker (local development)
	docker-compose up -d

.PHONY: docker-prod
docker-prod: ## Start all services with Docker (production)
	docker-compose -f docker-compose.prod.yml up -d

.PHONY: docker-build
docker-build: ## Build Docker images
	docker-compose build

.PHONY: docker-logs
docker-logs: ## View Docker logs
	docker-compose logs -f

.PHONY: docker-stop
docker-stop: ## Stop all Docker services
	docker-compose down

.PHONY: docker-clean
docker-clean: ## Stop and remove all Docker containers, volumes
	docker-compose down -v
	docker-compose -f docker-compose.prod.yml down -v

# Database Commands
.PHONY: db-init
db-init: ## Initialize database
	@echo "📊 Initializing database..."
	cd backend && python -c "from database import init_db; init_db()"
	@echo "✅ Database initialized"

.PHONY: db-reset
db-reset: ## Reset local SQLite database
	@echo "⚠️  Resetting local database..."
	@rm -f backend/sentinel_dev.db
	@echo "✅ Database reset. Will be recreated on next startup."

# Testing
.PHONY: test
test: ## Run tests
	@echo "🧪 Running tests..."
	cd backend && pytest
	npm test

.PHONY: test-api
test-api: ## Test API endpoints
	@echo "🧪 Testing API..."
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
	@curl -s http://localhost:8000/api/v1/config | python3 -m json.tool

# Deployment
.PHONY: deploy-prod
deploy-prod: ## Deploy to production (Docker)
	@echo "🚀 Deploying to production..."
	@echo "⚠️  Make sure you've configured production .env!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose -f docker-compose.prod.yml up -d --build
	@echo "✅ Deployed to production"

.PHONY: deploy-status
deploy-status: ## Check deployment status
	@echo "📊 Deployment Status:"
	@docker-compose -f docker-compose.prod.yml ps

# Cleanup
.PHONY: clean
clean: ## Clean up temporary files
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .next
	@rm -rf node_modules/.cache
	@echo "✅ Cleanup complete"

.PHONY: clean-all
clean-all: clean docker-clean db-reset ## Complete cleanup (Docker + DB + temp files)
	@echo "✅ Complete cleanup done"

# Ollama Management (Production)
.PHONY: ollama-pull
ollama-pull: ## Pull required Ollama models
	@echo "📥 Pulling Ollama models..."
	ollama pull gemma3:1b
	ollama pull gemma3:4b
	ollama pull gemma3:12b
	ollama pull embeddinggemma
	@echo "✅ Models downloaded"

.PHONY: ollama-list
ollama-list: ## List installed Ollama models
	@ollama list

# Utility Commands
.PHONY: generate-secret
generate-secret: ## Generate a secure SECRET_KEY
	@echo "Generated SECRET_KEY:"
	@python3 -c "import secrets; print(secrets.token_urlsafe(32))"

.PHONY: logs
logs: ## View application logs
	@echo "📋 Application Logs:"
	@tail -f logs/*.log 2>/dev/null || echo "No log files found"

.PHONY: health
health: ## Check health of all services
	@echo "🏥 Health Check:"
	@echo ""
	@echo "Backend API:"
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "❌ Backend not responding"
	@echo ""
	@echo "Redis:"
	@redis-cli ping 2>/dev/null || echo "❌ Redis not responding"
	@echo ""
	@echo "Neo4j:"
	@curl -s http://localhost:7474 >/dev/null && echo "✅ Neo4j is running" || echo "❌ Neo4j not responding"

# GCP Setup (Production)
.PHONY: gcp-setup-bucket
gcp-setup-bucket: ## Setup GCS bucket (interactive)
	@echo "🪣 Setting up GCS bucket..."
	@./scripts/setup_gcs.sh

.PHONY: gcp-setup-alloydb
gcp-setup-alloydb: ## Setup AlloyDB (interactive)
	@echo "🗄️  Setting up AlloyDB..."
	@./scripts/setup_alloydb.sh

# Documentation
.PHONY: docs
docs: ## Show documentation links
	@echo "📚 Documentation:"
	@echo "  - Deployment Guide:       DEPLOYMENT_GUIDE.md"
	@echo "  - Environment Switching:  ENVIRONMENT_SWITCHING.md"
	@echo "  - Environment Variables:  .env.example"
	@echo "  - API Documentation:      http://localhost:8000/api/v1/docs"

.PHONY: info
info: ## Show project information
	@echo "ℹ️  Sentinel AI - Document Intelligence Platform"
	@echo ""
	@echo "Current Environment:"
	@python3 check_env.py

# Default target
.DEFAULT_GOAL := help

