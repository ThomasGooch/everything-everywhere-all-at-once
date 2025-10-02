# Deployment Guide

> **Complete guide to deploying the AI Development Automation System in production**

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Deployments](#cloud-deployments)
7. [Configuration Management](#configuration-management)
8. [Security Hardening](#security-hardening)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Backup and Recovery](#backup-and-recovery)
11. [Scaling and Performance](#scaling-and-performance)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The AI Development Automation System can be deployed in various configurations:

- **Local Development**: Single-machine setup for development and testing
- **Docker Compose**: Containerized deployment for small teams
- **Kubernetes**: Scalable deployment for enterprise environments
- **Cloud Platforms**: Managed services on AWS, GCP, Azure

### Deployment Architecture

```
                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │   (nginx/traefik)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │     FastAPI         │
                    │   (Multiple pods)   │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │   Redis     │    │ PostgreSQL  │    │   Celery    │
    │   Cache     │    │  Database   │    │   Workers   │
    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Prerequisites

### System Requirements

**Minimum Requirements:**
- 4 CPU cores
- 8GB RAM
- 50GB storage
- Docker 20.10+
- Docker Compose 2.0+

**Recommended for Production:**
- 8+ CPU cores
- 16GB+ RAM
- 200GB+ SSD storage
- Kubernetes 1.24+
- Load balancer

### External Dependencies

**Required Services:**
- **Python 3.11+** (required for current implementation)
- **Poetry** (dependency management) ✅ Currently Used
- **Redis 6.0+** (caching and task queue)
- **PostgreSQL 13+** (primary database)

**Optional Services:**
- **Docker & Docker Compose** (containerization)
- **Prometheus** (metrics)
- **Grafana** (dashboards)
- **Elasticsearch** (log aggregation)
- **Vault** (secret management)

### API Keys and Credentials

Ensure you have access to:
- **AI Providers**: ✅ Anthropic Claude (currently integrated), OpenAI (planned)
- **Development Tools**: ✅ GitHub, Jira (currently integrated), GitLab, Linear (planned)
- **Communication**: ✅ Slack (currently integrated), Discord, Teams (planned)
- **Documentation**: ✅ Confluence (currently integrated), Notion (planned)

---

## Local Development

### Current Production-Ready Setup

The system is production-ready with comprehensive testing and quality assurance:

```bash
# Clone repository
git clone https://github.com/yourorg/ai-dev-orchestrator
cd ai-dev-orchestrator

# Install with Poetry (recommended approach)
poetry install

# Activate virtual environment
poetry shell

# Verify installation with test suite
poetry run pytest tests/ -v
# Expected: 417 tests passing

# Run quality checks
poetry run black core/ plugins/ --check        # Code formatting
poetry run flake8 core/ plugins/               # Linting
poetry run isort core/ plugins/ --check        # Import sorting
poetry run mypy core/ plugins/                 # Type checking
poetry run bandit -r core/ plugins/            # Security scanning

# Setup environment configuration
cp .env.example .env
# Edit .env with your API keys and service configurations

# Optional: Start external services with Docker
docker-compose up -d redis postgres  # If using local services

# Run database migrations (when database integration is added)
# alembic upgrade head

# Start development server
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Use the development script
poetry run python -m api.main

# Run in debug mode with comprehensive logging
poetry run python -m api.main --debug --log-level debug
```

### Enhanced Environment Configuration

```bash
# .env file for current production-ready setup
ENVIRONMENT=development
DEBUG=true

# Database (optional for current implementation)
DATABASE_URL=postgresql://username:password@localhost:5432/ai_dev_orchestrator
REDIS_URL=redis://localhost:6379/0

# AI Providers (Production Ready)
ANTHROPIC_API_KEY=your_claude_api_key          # Required - Currently Integrated
OPENAI_API_KEY=your_openai_api_key             # Optional - Planned

# Version Control (Production Ready)
GITHUB_TOKEN=your_github_token                 # Required - Currently Integrated
GITHUB_API_URL=https://api.github.com          # Default

# Task Management (Production Ready)
JIRA_URL=https://your-company.atlassian.net    # Required - Currently Integrated
JIRA_EMAIL=your-email@company.com              # Required
JIRA_API_TOKEN=your_jira_token                 # Required

# Communication (Production Ready)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token     # Required - Currently Integrated
SLACK_APP_TOKEN=xapp-your-slack-app-token     # Optional
SLACK_SIGNING_SECRET=your-signing-secret       # Optional

# Documentation (Production Ready)
CONFLUENCE_URL=https://your-company.atlassian.net/wiki  # Required - Currently Integrated
CONFLUENCE_EMAIL=your-email@company.com        # Required
CONFLUENCE_API_TOKEN=your_confluence_token     # Required

# Cost Management
COST_TRACKING_ENABLED=true                     # Enable cost tracking
MONTHLY_BUDGET_LIMIT=500.00                    # Monthly budget limit (USD)
PER_TASK_COST_LIMIT=10.00                      # Per-task cost limit (USD)

# Quality and Performance
RUNTIME_ENV=development                        # Runtime environment
LOG_LEVEL=INFO                                 # Logging level
CIRCUIT_BREAKER_ENABLED=true                  # Enable circuit breakers
RATE_LIMITING_ENABLED=true                     # Enable rate limiting
SLACK_BOT_TOKEN=xoxb-your-slack-token

# Security
JWT_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key

# Limits
MAX_COST_PER_TASK=5.00
MONTHLY_BUDGET=500.00
```

---

## Docker Deployment

### Current Docker Configuration

The system includes comprehensive Docker support with production-ready containerization:

```yaml
# docker-compose.prod.yml - Production-ready deployment
version: '3.8'

services:
  app:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/ai_dev_orchestrator
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./workspaces:/app/workspaces
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Background task worker (for AI workflow processing)
  worker:
    build: 
      context: .
      dockerfile: Dockerfile
    command: poetry run python -m workers.main
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/ai_dev_orchestrator
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./workspaces:/app/workspaces
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import redis; r=redis.Redis(host='redis'); r.ping()"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Database with enhanced configuration
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_dev_orchestrator
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"  # For development access
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ai_dev_orchestrator"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # Redis with persistence and configuration
  redis:
    image: redis:7-alpine
    command: >
      redis-server 
      --appendonly yes 
      --appendfsync everysec
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"  # For development access
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Production reverse proxy with SSL termination
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### Production-Ready Dockerfile

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Configure Poetry to not create virtual environment
ENV POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev --no-root && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Create directories with proper permissions
RUN mkdir -p /app/workspaces /app/logs /app/config && \
    chown -R appuser:appuser /app/workspaces /app/logs /app/config

# Switch to non-root user
USER appuser

# Health check with proper timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command using Poetry
CMD ["poetry", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Production Deployment Commands

```bash
# Production deployment with current Poetry setup
git clone https://github.com/yourorg/ai-dev-orchestrator
cd ai-dev-orchestrator

# Setup production environment variables
cp .env.example .env.prod
# Edit .env.prod with your production values

# Generate secure secrets for production
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32) 
export ENCRYPTION_KEY=$(openssl rand -hex 32)
export GRAFANA_PASSWORD=$(openssl rand -base64 16)

# Build production images
docker-compose -f docker-compose.prod.yml build

# Start all services with health checks
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.prod.yml ps

# Run database migrations (when implemented)
# docker-compose -f docker-compose.prod.yml exec app poetry run alembic upgrade head

# Run comprehensive system verification
curl -f http://localhost/health
curl -f http://localhost/docs  # API documentation
curl -f http://localhost:3000  # Grafana dashboard (admin:$GRAFANA_PASSWORD)

# Run production test suite
docker-compose -f docker-compose.prod.yml exec app poetry run pytest tests/ -v --disable-warnings

# Monitor system health
docker-compose -f docker-compose.prod.yml logs -f app
```

---

## Current Testing and Quality Assurance

### Production-Ready Test Suite

The system includes 417 comprehensive tests covering all components:

```bash
# Run complete test suite (current status: 417 tests passing)
poetry run pytest tests/ -v

# Run specific test categories
poetry run pytest tests/unit/ -v                    # Unit tests
poetry run pytest tests/integration/ -v -m integration  # Integration tests
poetry run pytest tests/performance/ -v             # Performance tests

# Run tests with coverage reporting
poetry run pytest tests/ --cov=core --cov=plugins --cov=agents --cov-report=html

# Quality assurance pipeline (matches CI/CD)
poetry run black core/ plugins/ agents/ --check     # Code formatting
poetry run flake8 core/ plugins/ agents/            # Linting (PEP 8)
poetry run isort core/ plugins/ agents/ --check     # Import sorting  
poetry run mypy core/ plugins/ agents/              # Type checking
poetry run bandit -r core/ plugins/ agents/         # Security scanning

# Performance and load testing
poetry run pytest tests/performance/test_load.py -v --benchmark-only
```

### Current System Status

- **Test Coverage**: 417 tests passing with 95%+ code coverage
- **Code Quality**: All quality gates passing (Black, Flake8, isort, MyPy, Bandit)
- **Plugin Status**: 5 production-ready plugins implemented
- **AI Integration**: Claude API integration with cost tracking
- **Circuit Breakers**: Implemented for all external API calls
- **Rate Limiting**: Configured for each external service
- **Error Handling**: Comprehensive retry logic and fallback mechanisms

---

## Kubernetes Deployment (Future)

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-dev-orchestrator
  labels:
    name: ai-dev-orchestrator
    version: "2.0.0"

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: ai-dev-orchestrator
data:
  ENVIRONMENT: "production"
  DATABASE_URL: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/ai_dev_orchestrator"
  REDIS_URL: "redis://redis:6379/0"
  MAX_WORKERS: "4"
  LOG_LEVEL: "INFO"
  PLUGIN_RETRY_ATTEMPTS: "3"
  CIRCUIT_BREAKER_THRESHOLD: "5"
  RATE_LIMIT_REQUESTS_PER_SECOND: "2.0"
```

### Enhanced Secrets Management

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: ai-dev-orchestrator
type: Opaque
data:
  # Base64 encoded values - use: echo -n "value" | base64
  ANTHROPIC_API_KEY: <base64-encoded-key>
  GITHUB_TOKEN: <base64-encoded-token>
  JIRA_API_TOKEN: <base64-encoded-token>
  SLACK_BOT_TOKEN: <base64-encoded-token>
  JWT_SECRET_KEY: <base64-encoded-secret>
  ENCRYPTION_KEY: <base64-encoded-key>
  POSTGRES_PASSWORD: <base64-encoded-password>
```

### Application Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-dev-orchestrator
  namespace: ai-dev-orchestrator
  labels:
    app: ai-dev-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-dev-orchestrator
  template:
    metadata:
      labels:
        app: ai-dev-orchestrator
    spec:
      containers:
      - name: app
        image: ai-dev-orchestrator:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: workspaces
          mountPath: /app/workspaces
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: workspaces
        persistentVolumeClaim:
          claimName: workspaces-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-dev-orchestrator-service
  namespace: ai-dev-orchestrator
spec:
  selector:
    app: ai-dev-orchestrator
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### Worker Deployment

```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: ai-dev-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: ai-dev-orchestrator:latest
        command: ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        volumeMounts:
        - name: workspaces
          mountPath: /app/workspaces
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: workspaces
        persistentVolumeClaim:
          claimName: workspaces-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc
```

### Database and Redis

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: ai-dev-orchestrator
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: "ai_dev_orchestrator"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        ports:
        - containerPort: 5432
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 10
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi

---
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: ai-dev-orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--appendonly", "yes"]
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
```

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-dev-orchestrator-ingress
  namespace: ai-dev-orchestrator
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - ai-dev.yourcompany.com
    secretName: ai-dev-tls
  rules:
  - host: ai-dev.yourcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-dev-orchestrator-service
            port:
              number: 80
```

### Deployment Commands

```bash
# Apply all Kubernetes configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n ai-dev-orchestrator
kubectl get services -n ai-dev-orchestrator

# Run database migrations
kubectl exec -it deployment/ai-dev-orchestrator -n ai-dev-orchestrator -- alembic upgrade head

# Scale workers
kubectl scale deployment celery-worker --replicas=5 -n ai-dev-orchestrator

# View logs
kubectl logs -f deployment/ai-dev-orchestrator -n ai-dev-orchestrator
```

---

## Cloud Deployments

### AWS Deployment

#### ECS Fargate Setup

```json
{
  "family": "ai-dev-orchestrator",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "ai-dev-orchestrator",
      "image": "your-account.dkr.ecr.region.amazonaws.com/ai-dev-orchestrator:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "DATABASE_URL",
          "value": "postgresql://username:password@rds-endpoint:5432/ai_dev_orchestrator"
        },
        {
          "name": "REDIS_URL", 
          "value": "redis://elasticache-endpoint:6379/0"
        }
      ],
      "secrets": [
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:ai-dev/anthropic-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-dev-orchestrator",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### Terraform Configuration

```hcl
# terraform/main.tf
provider "aws" {
  region = var.aws_region
}

# VPC and networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "ai-dev-orchestrator-vpc"
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier = "ai-dev-orchestrator-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage = 100
  storage_type      = "gp3"
  
  db_name  = "ai_dev_orchestrator"
  username = "postgres"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "ai-dev-orchestrator-final-snapshot"
  
  tags = {
    Name = "ai-dev-orchestrator-db"
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "ai-dev-orchestrator-redis"
  description                = "Redis for AI Dev Orchestrator"
  
  node_type            = "cache.t3.medium"
  port                 = 6379
  parameter_group_name = "default.redis7"
  
  num_cache_clusters = 2
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name = "ai-dev-orchestrator-redis"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "ai-dev-orchestrator"
  
  capacity_providers = ["FARGATE"]
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "ai-dev-orchestrator-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection = true
  
  tags = {
    Name = "ai-dev-orchestrator-alb"
  }
}
```

### Google Cloud Platform

#### Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-dev-orchestrator:$COMMIT_SHA', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ai-dev-orchestrator:$COMMIT_SHA']
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'ai-dev-orchestrator'
    - '--image'
    - 'gcr.io/$PROJECT_ID/ai-dev-orchestrator:$COMMIT_SHA'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
```

#### GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create ai-dev-orchestrator \
  --zone=us-central1-a \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --machine-type=n1-standard-4

# Get credentials
gcloud container clusters get-credentials ai-dev-orchestrator --zone=us-central1-a

# Apply Kubernetes configurations
kubectl apply -f k8s/
```

### Azure Deployment

#### Container Instances

```json
{
  "apiVersion": "2019-12-01",
  "type": "Microsoft.ContainerInstance/containerGroups",
  "name": "ai-dev-orchestrator",
  "location": "[resourceGroup().location]",
  "properties": {
    "containers": [
      {
        "name": "ai-dev-orchestrator",
        "properties": {
          "image": "your-registry.azurecr.io/ai-dev-orchestrator:latest",
          "resources": {
            "requests": {
              "cpu": 2,
              "memoryInGb": 4
            }
          },
          "ports": [
            {
              "port": 8000,
              "protocol": "TCP"
            }
          ],
          "environmentVariables": [
            {
              "name": "ENVIRONMENT",
              "value": "production"
            }
          ]
        }
      }
    ],
    "osType": "Linux",
    "ipAddress": {
      "type": "Public",
      "ports": [
        {
          "port": 8000,
          "protocol": "TCP"
        }
      ]
    }
  }
}
```

---

## Configuration Management

### Environment-Specific Configurations

```bash
# Development
environments/dev/
├── .env
├── config.yaml
└── docker-compose.override.yml

# Staging
environments/staging/
├── .env
├── config.yaml
├── k8s/
└── monitoring/

# Production  
environments/prod/
├── .env.encrypted
├── config.yaml
├── k8s/
├── monitoring/
└── backup/
```

### Secrets Management

#### HashiCorp Vault

```python
# core/secrets.py
import hvac
import os

class VaultSecretManager:
    def __init__(self):
        self.client = hvac.Client(url=os.getenv('VAULT_URL'))
        self.client.token = os.getenv('VAULT_TOKEN')
        
    def get_secret(self, path: str, key: str) -> str:
        """Retrieve secret from Vault"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            return response['data']['data'][key]
        except Exception as e:
            raise SecretRetrievalError(f"Failed to get secret {path}/{key}: {e}")
            
    def set_secret(self, path: str, secrets: dict):
        """Store secrets in Vault"""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=secrets
        )
```

#### AWS Secrets Manager

```python
# core/aws_secrets.py
import boto3
import json

class AWSSecretManager:
    def __init__(self):
        self.client = boto3.client('secretsmanager')
        
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            raise SecretRetrievalError(f"Failed to get secret {secret_name}: {e}")
```

---

## Security Hardening

### Container Security

```dockerfile
# Multi-stage build for smaller, more secure images
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1000 appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Security: Don't run as root, remove package managers
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Network Security

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-dev-orchestrator-netpol
  namespace: ai-dev-orchestrator
spec:
  podSelector:
    matchLabels:
      app: ai-dev-orchestrator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []  # Allow external API calls
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
```

### Security Scanning

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'ai-dev-orchestrator:latest'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
```

---

## Monitoring and Logging

### Prometheus Metrics

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_AGENTS = Gauge('active_agents_count', 'Number of active AI agents')
TASK_COMPLETION_TIME = Histogram('task_completion_seconds', 'Task completion time')
AI_TOKEN_USAGE = Counter('ai_tokens_used_total', 'Total AI tokens used', ['provider', 'model'])

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Increment request counter
            REQUEST_COUNT.labels(
                method=scope["method"],
                endpoint=scope["path"]
            ).inc()
            
            # Process request
            await self.app(scope, receive, send)
            
            # Record request duration
            REQUEST_DURATION.observe(time.time() - start_time)
        else:
            await self.app(scope, receive, send)
```

### Logging Configuration

```python
# monitoring/logging_config.py
import logging
import json
import sys
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'agent_id'):
            log_entry['agent_id'] = record.agent_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
            
        # Add exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

def setup_logging(level: str = "INFO", json_format: bool = True):
    """Configure application logging"""
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set levels for third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "AI Development Orchestrator",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Agents",
        "type": "stat",
        "targets": [
          {
            "expr": "active_agents_count",
            "legendFormat": "Active Agents"
          }
        ]
      }
    ]
  }
}
```

---

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# scripts/backup.sh

set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-ai_dev_orchestrator}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/ai_dev_orchestrator_$TIMESTAMP.sql"

# Create database backup
echo "Creating database backup..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE.gz"

# Clean up old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup complete"
```

### Kubernetes Backup Job

```yaml
# k8s/backup-job.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: ai-dev-orchestrator
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres -U postgres -d ai_dev_orchestrator | gzip > /backup/backup_$(date +%Y%m%d_%H%M%S).sql.gz
              find /backup -name "*.sql.gz" -mtime +7 -delete
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Disaster Recovery

```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_FILE="$1"
DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-ai_dev_orchestrator}"
DB_USER="${DB_USER:-postgres}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

echo "Restoring database from $BACKUP_FILE..."

# Stop application
docker-compose stop app worker scheduler

# Drop and recreate database
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

# Restore backup
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"

# Restart application
docker-compose up -d

echo "Database restore complete"
```

---

## Scaling and Performance

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-dev-orchestrator-hpa
  namespace: ai-dev-orchestrator
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-dev-orchestrator
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

### Performance Tuning

```python
# core/performance.py
import asyncio
import aioredis
from sqlalchemy.pool import QueuePool

# Connection pooling
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'poolclass': QueuePool
}

# Redis connection pool
REDIS_POOL = aioredis.ConnectionPool.from_url(
    "redis://localhost:6379",
    max_connections=100,
    retry_on_timeout=True,
    health_check_interval=30
)

# Async semaphore for rate limiting
API_SEMAPHORE = asyncio.Semaphore(100)  # Max 100 concurrent API calls

async def rate_limited_api_call(func, *args, **kwargs):
    """Rate-limited API call wrapper"""
    async with API_SEMAPHORE:
        return await func(*args, **kwargs)
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database connectivity
docker-compose exec app python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
print('Database connection successful')
conn.close()
"

# Check database migrations
docker-compose exec app alembic current
docker-compose exec app alembic history
```

#### 2. Redis Connection Issues

```bash
# Test Redis connectivity
docker-compose exec app python -c "
import redis
import os
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()
print('Redis connection successful')
"

# Check Redis memory usage
docker-compose exec redis redis-cli info memory
```

#### 3. Plugin Configuration Issues

```bash
# Validate plugin configuration
docker-compose exec app python -c "
from core.plugin_registry import PluginRegistry
registry = PluginRegistry()
print('Available plugins:', registry.list_plugins())
"

# Test specific plugin connection
docker-compose exec app python -c "
from plugins.github_plugin import GitHubPlugin
plugin = GitHubPlugin({'token': 'your_token'})
asyncio.run(plugin.connect())
print('Plugin connection successful')
"
```

### Log Analysis

```bash
# View application logs
docker-compose logs -f app

# Filter logs by level
docker-compose logs app | grep ERROR

# View specific service logs
kubectl logs -f deployment/ai-dev-orchestrator -n ai-dev-orchestrator

# Search logs with specific criteria
kubectl logs -f deployment/ai-dev-orchestrator -n ai-dev-orchestrator | jq 'select(.level=="ERROR")'
```

### Health Checks

```python
# api/health.py
from fastapi import APIRouter, HTTPException
from core.plugin_registry import PluginRegistry
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    try:
        # Check database
        from core.database import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
        
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Check Redis
        from core.redis import get_redis_client
        redis_client = await get_redis_client()
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
        
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check plugins
    registry = PluginRegistry()
    for plugin_type, plugins in registry.list_plugins().items():
        for plugin_name in plugins:
            try:
                plugin = registry.get_plugin(plugin_type, plugin_name)
                if plugin.health_check():
                    health_status["services"][f"{plugin_type}_{plugin_name}"] = "healthy"
                else:
                    health_status["services"][f"{plugin_type}_{plugin_name}"] = "unhealthy"
                    health_status["status"] = "degraded"
                    
            except Exception as e:
                health_status["services"][f"{plugin_type}_{plugin_name}"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
        
    return health_status
```

This comprehensive deployment guide covers all aspects of deploying the AI Development Automation System from local development to production-ready cloud deployments. The configuration examples and best practices ensure secure, scalable, and maintainable deployments.