# Implementation Order - Quick Reference

## Week 1: Database & Foundation

### Day 1-2: PostgreSQL Setup
```bash
# Install dependencies
cd mcp-server
uv sync

# Update .env with PostgreSQL connection
cp .env.example .env
# Edit: DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/workflow_orchestrator

# Initialize Alembic
uv run alembic init alembic

# Create initial migration
uv run alembic revision --autogenerate -m "Initial schema"
uv run alembic upgrade head
```

**Files to create**:
- `mcp-server/src/database/__init__.py` - SQLAlchemy async engine
- `mcp-server/src/models/database.py` - User, Task, TaskAuditLog models
- `mcp-server/alembic/env.py` - Alembic configuration

**Test**: `uv run python -c "from src.database import engine; print('✅ DB connected')"`

### Day 3: OAuth Implementation
**Files to create**:
- `mcp-server/src/auth/oauth.py` - `/oauth/authorize`, `/oauth/token` endpoints
- `mcp-server/src/auth/middleware.py` - `get_current_user()` dependency

**Test**:
```bash
curl http://localhost:8000/oauth/authorize?redirect_uri=http://localhost:3000/callback
```

---

## Week 2: Core MCP Tools

### Day 4-5: Task Management Tools
**Files to create**:
- `mcp-server/src/tools/tasks.py` - All 3 task tools
- `mcp-server/src/services/task_service.py` - Business logic

**Implementation order**:
1. `create_task_tool` - Simplest, no dependencies
2. `list_tasks_tool` - Adds filtering logic
3. `update_task_status_tool` - Adds audit logging

**Test each tool**: `uv run pytest tests/test_tasks.py -v`

### Day 6: Email Integration
**Files to create**:
- `mcp-server/src/tools/integrations.py` - `trigger_integration_tool`
- `mcp-server/src/services/email_service.py` - SMTP email sender

**Test**:
```python
from src.services.email_service import send_email
await send_email("test@example.com", "Test", "Hello")
```

---

## Week 3: UI Components

### Day 7-8: MCP UI Resources
**Files to create**:
- `mcp-server/src/ui/resources.py` - Declare UI resources
- Update `main.py` to register resources with `@mcp.list_resources()`

**Files to update**:
- All tool files to return `CallToolResult` with `_meta["ui/resourceUri"]`

### Day 9-10: React Components
**Files to create**:
- `ui/src/components/Tasks/TaskCard.tsx`
- `ui/src/components/Tasks/TaskTable.tsx`
- `ui/src/components/Tasks/StatusUpdate.tsx`
- `ui/src/components/Integrations/EmailConfirmation.tsx`

**Each component must**:
- Access `(window as any).openai.toolResponseMetadata`
- Read `_meta` for rich data
- Use ShadCN UI components

---

## Week 4: Docker & Deployment

### Day 11: Docker Compose
**Files to update**:
- `docker-compose.yml` - Add PostgreSQL service
- `docker/Dockerfile.mcp-server` - Add migration step
- Create `docker/docker-entrypoint.sh`

**Test**:
```bash
docker-compose up -d postgres
docker-compose up -d redis
docker-compose up mcp-server
```

### Day 12: VPS Deployment
**Files to create**:
- `deploy/docker-compose.prod.yml`
- `deploy/nginx.conf`
- `deploy/.env.example`

**Deployment steps**:
```bash
# On VPS
git clone <repo>
cd smart-info-navigator
cp deploy/.env.example deploy/.env
# Edit deploy/.env with production values
docker-compose -f deploy/docker-compose.prod.yml up -d
```

---

## Testing Checklist

### Local Testing
- [ ] PostgreSQL connection works
- [ ] Alembic migrations run successfully
- [ ] OAuth flow completes
- [ ] JWT tokens validate correctly
- [ ] `create_task` creates in database
- [ ] `list_tasks` filters work
- [ ] `update_task_status` updates status
- [ ] Email sends via SMTP
- [ ] React components render in browser
- [ ] Docker Compose starts all services

### Production Testing (VPS)
- [ ] HTTPS works with SSL cert
- [ ] OAuth redirect to production domain works
- [ ] Database persists across restarts
- [ ] Email sends from production SMTP
- [ ] ChatGPT can connect to MCP server
- [ ] UI components render in ChatGPT
- [ ] Rate limiting works
- [ ] Logs are accessible

---

## Quick Commands Reference

### Development
```bash
# Start PostgreSQL only
docker-compose up -d postgres

# Run MCP server manually (for debugging)
cd mcp-server
uv run uvicorn src.main:app --reload

# Run React UI manually
cd ui
npm run dev

# Run migrations
cd mcp-server
uv run alembic upgrade head

# Run tests
uv run pytest -v

# Type check
uv run mypy src/
```

### Production
```bash
# Deploy to VPS
ssh user@vps-ip
cd /opt/workflow-orchestrator
git pull
docker-compose -f deploy/docker-compose.prod.yml up -d --build

# View logs
docker-compose -f deploy/docker-compose.prod.yml logs -f mcp-server

# Run migration on production
docker-compose -f deploy/docker-compose.prod.yml exec mcp-server uv run alembic upgrade head

# Backup database
docker-compose -f deploy/docker-compose.prod.yml exec postgres pg_dump -U workflow_user workflow_orchestrator > backup.sql
```

---

## Dependencies Installation

### System Requirements
- Python 3.11+
- Node.js 20+
- UV package manager
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)

### Install UV
```bash
pip install uv
```

### Install Node Dependencies
```bash
cd ui
npm install
```

### Install Python Dependencies
```bash
cd mcp-server
uv sync
```

---

## Environment Variables Checklist

### Required for Local Development
```env
# mcp-server/.env
DATABASE_URL=postgresql+asyncpg://workflow_user:workflow_password@localhost:5432/workflow_orchestrator
REDIS_URL=redis://localhost:6379
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
JWT_SECRET=your-secret-key-min-32-chars
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### Required for Production
- All above variables
- `ALLOWED_ORIGINS=https://chat.openai.com,https://chatgpt.com`
- `DEBUG=false`
- SSL certificates in `/etc/nginx/ssl/`

---

## Common Issues & Solutions

### Issue: Alembic can't connect to database
**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL
```

### Issue: OAuth redirect fails
**Solution**:
- Verify `ALLOWED_ORIGINS` includes ChatGPT domain
- Check redirect URI matches exactly

### Issue: Email sending fails
**Solution**:
- Use app-specific password for Gmail
- Enable "Less secure app access" or use OAuth2 for Gmail
- Check SMTP credentials

### Issue: UI components don't render
**Solution**:
- Verify `ui/resourceUri` in tool responses
- Check `@mcp.list_resources()` is registered
- Look for CORS errors in browser console

---

## Success Criteria for MVP

✅ **Epic 1: Foundation**
- MCP server accessible via HTTPS
- Tools discoverable by ChatGPT
- UI components render in ChatGPT

✅ **Epic 2: Authentication**
- OAuth flow completes successfully
- Users authenticated via JWT
- Sessions scoped per user

✅ **Epic 3: Core Tools**
- Tasks can be created, listed, updated
- Filters work (status, priority, overdue)
- Email notifications send successfully
- Audit log records changes

**MVP Complete**: All 3 epics checked ✅
