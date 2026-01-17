# Docker Deployment Guide

This guide explains how to deploy Task Manager using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

Install Docker:
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify installation
docker --version
docker-compose --version
```

## Quick Start

### 1. Configure Environment

Create `.env` file from example:
```bash
cp .env.docker.example .env
```

Edit `.env` and set your API key:
```bash
# Generate secure API key
openssl rand -hex 32

# Edit .env and paste the generated key
nano .env
```

### 2. Build and Start

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

The application will be available at:
- Frontend: http://localhost:80
- Backend API: http://localhost:8000

### 3. Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes all data!)
docker-compose down -v
```

## Architecture

```
┌─────────────────┐
│   Frontend      │  Port 80
│   (Nginx)       │
└────────┬────────┘
         │ proxy /api
         ▼
┌─────────────────┐
│   Backend       │  Port 8000
│   (FastAPI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Volumes       │
│  - Database     │
│  - Backups      │
│  - Logs         │
└─────────────────┘
```

## Services

### Backend
- **Image**: Python 3.11
- **Port**: 8000
- **Volumes**:
  - `task-manager-db`: SQLite database (`/data/db`)
  - `task-manager-backups`: Backup files (`/data/backups`)
  - `task-manager-logs`: Application logs (`/data/logs`)

### Frontend
- **Image**: Node 20 (build) + Nginx Alpine (runtime)
- **Port**: 80
- **Features**:
  - SPA routing support
  - API proxy to backend
  - Gzip compression
  - Static asset caching

## Volume Management

### List Volumes
```bash
docker volume ls | grep task-manager
```

### Backup Data
```bash
# Backup database
docker run --rm -v task-manager-db:/data -v $(pwd):/backup \
  alpine tar czf /backup/db-backup.tar.gz /data

# Backup all volumes
docker run --rm \
  -v task-manager-db:/data/db \
  -v task-manager-backups:/data/backups \
  -v task-manager-logs:/data/logs \
  -v $(pwd):/backup \
  alpine tar czf /backup/full-backup.tar.gz /data
```

### Restore Data
```bash
# Restore database
docker run --rm -v task-manager-db:/data -v $(pwd):/backup \
  alpine sh -c "cd / && tar xzf /backup/db-backup.tar.gz"
```

### Access Volume Data
```bash
# Open shell in backend container
docker-compose exec backend sh

# View database location
ls -la /data/db/

# View backups
ls -la /data/backups/

# View logs
tail -f /data/logs/app.log
```

## Scheduler Status

The auto backup scheduler runs inside the backend container and executes checks every minute.

### View Scheduler Logs
```bash
# Follow all backend logs
docker-compose logs -f backend

# Filter for scheduler logs
docker-compose logs -f backend | grep scheduler

# Filter for backup logs
docker-compose logs -f backend | grep -E "🔍|⏰|📊|✨|⏸️"
```

You should see logs every minute like:
```
🔍 Auto backup check: enabled=True, current=21:36, target=03:00, interval=1d
⏳ Waiting for backup time (current=21:36, need=03:00)
```

### Verify Scheduler is Running
```bash
# Check backend startup logs
docker-compose logs backend | grep "scheduler started"

# Should show:
# ==================================================
# Background scheduler started successfully
# Scheduled jobs: ['check_auto_roll', 'check_auto_penalties', 'check_auto_backup']
# Auto backup job will run every minute
# ==================================================
```

## Troubleshooting

### Check Container Health
```bash
docker-compose ps
# Both services should show "healthy" status
```

### View Container Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend

# Follow logs (real-time)
docker-compose logs -f backend
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Rebuild After Code Changes
```bash
# Rebuild and restart
docker-compose up -d --build

# Force rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

### Check Backend Health
```bash
curl http://localhost:8000/
# Should return: {"message":"Task Manager API","status":"active"}
```

### Check Frontend
```bash
curl http://localhost/
# Should return HTML
```

### Permission Issues
If you encounter permission issues with volumes:
```bash
# Stop services
docker-compose down

# Remove volumes
docker volume rm task-manager-db task-manager-backups task-manager-logs

# Restart
docker-compose up -d
```

## Production Deployment

### 1. Use Production Ports
Edit `docker-compose.yml` to change frontend port if needed:
```yaml
frontend:
  ports:
    - "8080:80"  # Change from 80 to avoid conflicts
```

### 2. Enable HTTPS
Add SSL certificates and configure nginx:
```yaml
frontend:
  volumes:
    - ./ssl:/etc/nginx/ssl:ro
```

Update `frontend/nginx.conf` to add SSL configuration.

### 3. Set Strong API Key
```bash
# Generate strong key
openssl rand -hex 32

# Set in .env
TASK_MANAGER_API_KEY=<generated-key>
```

### 4. Regular Backups
Set up automatic volume backups with cron:
```bash
# Add to crontab (crontab -e)
0 2 * * * cd /path/to/task-manager && ./scripts/backup-docker-volumes.sh
```

### 5. Monitor Logs
Use log aggregation tools:
- Docker built-in logging drivers
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- CloudWatch (AWS)

### 6. Resource Limits
Add resource limits in `docker-compose.yml`:
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

## Updates

### Pull Latest Code
```bash
git pull origin main
docker-compose up -d --build
```

### Update Only Backend
```bash
docker-compose up -d --build backend
```

### Update Only Frontend
```bash
docker-compose up -d --build frontend
```

## Development vs Production

For **development**, you can mount source code as volumes for hot-reload:

```yaml
# docker-compose.dev.yml
services:
  backend:
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## FAQ

**Q: How do I access the database directly?**
```bash
docker-compose exec backend sh
cd /data/db
sqlite3 tasks.db
```

**Q: Backups not working?**
Check scheduler logs:
```bash
docker-compose logs backend | grep -E "backup|scheduler"
```

**Q: Frontend can't reach backend?**
Check network connectivity:
```bash
docker-compose exec frontend ping backend
```

**Q: How do I clear all data?**
```bash
docker-compose down -v  # ⚠️ WARNING: Deletes all data!
```

**Q: Can I run this on a different port?**
Yes, edit `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "8080:80"  # Access at http://localhost:8080
```

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Check health: `docker-compose ps`
- Restart services: `docker-compose restart`
- Review documentation: README.md

