# AgentLink Deployment Guide

## Prerequisites

- Docker Engine 24.0+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

## Quick Deploy

### 1. Clone Repository

```bash
git clone http://YOUR_GITEA_URL/claude/agentlink.git
# Or use GitHub: git clone https://github.com/tilleulenspiegel/agentlink.git
cd agentlink
```

### 2. Start Services

```bash
docker compose up -d
```

### 3. Verify Deployment

```bash
# Check services
docker compose ps

# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","states_count":N,"timestamp":"..."}
```

### 4. Access API Documentation

Open http://localhost:8000/docs in your browser for interactive API docs.

## Service Ports

| Service    | Port | Description                    |
|------------|------|--------------------------------|
| Backend    | 8000 | FastAPI application            |
| PostgreSQL | 5432 | State database                 |
| Redis      | 6379 | Pub/Sub (Phase 3)              |
| ChromaDB   | 8001 | Vector search (Phase 3)        |

## Configuration

### Environment Variables

Create `.env` in project root:

```env
# Database
POSTGRES_USER=agentlink
POSTGRES_PASSWORD=YOUR_DB_PASSWORD
POSTGRES_DB=agentlink

# Backend
API_HOST=0.0.0.0
API_PORT=8000

# Redis (Phase 3)
REDIS_URL=redis://redis:6379

# ChromaDB (Phase 3)
CHROMA_URL=http://chromadb:8001
```

### Docker Compose

The stack includes:

```yaml
services:
  backend:    # FastAPI application
  postgres:   # State persistence
  redis:      # Real-time Pub/Sub (future)
  chromadb:   # Semantic search (future)
```

## Database Initialization

On first startup, PostgreSQL automatically:
1. Creates `agentlink` database
2. Creates `agent_states` table via SQLAlchemy
3. Ready for state storage

**No manual migrations needed for MVP!**

## Persistence

Data is persisted in Docker volumes:

```bash
# List volumes
docker volume ls | grep agentlink

# Backup database
docker compose exec postgres pg_dump -U agentlink agentlink > backup.sql

# Restore database
docker compose exec -T postgres psql -U agentlink agentlink < backup.sql
```

## Monitoring

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres
```

### Database Access

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U agentlink

# Query states
SELECT id, agent_id, timestamp FROM agent_states;

# Exit
\q
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker compose logs backend

# Common issue: PostgreSQL not ready
# Solution: Backend auto-retries, wait 30s
```

### Port conflicts

```bash
# Check what's using port 8000
lsof -i :8000

# Change port in docker-compose.yml:
ports:
  - "8001:8000"  # Use 8001 externally
```

### Database connection refused

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Restart if needed
docker compose restart postgres
```

### Reset everything

```bash
# Stop and remove all data
docker compose down -v

# Fresh start
docker compose up -d
```

## Production Deployment

### Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Use secrets management (not .env)
- [ ] Enable SSL/TLS for API
- [ ] Configure firewall rules
- [ ] Set up backup automation
- [ ] Enable logging to external service
- [ ] Add authentication to API endpoints

### Scaling

**Single Instance (MVP):**
- Good for 1-5 agents
- ~100 states/second
- No special setup needed

**Multi-Instance (Future):**
- Load balancer (nginx/traefik)
- Shared PostgreSQL
- Redis Pub/Sub for state sync
- ChromaDB for semantic search

### Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=20260223
docker compose exec postgres pg_dump -U agentlink agentlink | gzip > backup-.sql.gz

# Keep last 7 days
find . -name "backup-*.sql.gz" -mtime +7 -delete
```

Add to crontab:
```cron
0 2 * * * /path/to/backup.sh
```

## Updating

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Check health
curl http://localhost:8000/health
```

## Current Deployment

**VM:** YOUR_VM_IP
- Ubuntu 24.04 LTS
- User: claude
- Docker version: 27.5.0
- Docker Compose version: 2.31.0

**Access:**
- API: http://YOUR_VM_IP:8000
- Docs: http://YOUR_VM_IP:8000/docs
- Database: YOUR_VM_IP:5432

**Status:** ✅ Running (Phase 1 MVP complete)

## Next Steps

1. ✅ Backend deployed
2. ✅ Client library built
3. ✅ First handoff validated
4. 🔌 Next: OpenClaw plugin integration
