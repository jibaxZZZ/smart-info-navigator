# Workflow Orchestrator - MVP Implementation Plan

**Version**: 1.0
**Date**: 2026-01-03
**Scope**: Epic 1 (Foundation), Epic 2 (Auth), Epic 3 (Core Tools)

---

## 🎯 MVP Objectives

Build a production-ready ChatGPT App that:
1. ✅ Complies with OpenAI ChatGPT Apps requirements
2. ✅ Authenticates users via OAuth 2.0
3. ✅ Provides core task management (create, list, update)
4. ✅ Returns rich UI components rendered in ChatGPT
5. ✅ Uses PostgreSQL for data persistence
6. ✅ Supports email notifications
7. ✅ Deploys to VPS via Docker

**Deferred to Phase 2**: Reports, Jira/Slack integration, workflow scheduling

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         ChatGPT Client                       │
│  (Natural language → MCP protocol → Tool selection)         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS + OAuth
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Tools (No AI/LLM calls)                         │  │
│  │  • create_task    • list_tasks    • update_task      │  │
│  │  • trigger_integration (email only)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Business Logic Layer                                │  │
│  │  • Task CRUD     • Email sender    • Session mgmt    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────┬───────────────────────┬───────────────────────────┘
          │                       │
          ▼                       ▼
   ┌──────────────┐      ┌──────────────┐
   │  PostgreSQL  │      │     Redis    │
   │   Database   │      │   Sessions   │
   └──────────────┘      └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    React UI Components                       │
│  (Rendered in ChatGPT iframe via MCP UI resources)          │
│  • TaskCard    • TaskTable    • StatusBadge                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂 Database Schema

### PostgreSQL Tables

```sql
-- Users table (OAuth identity)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oauth_sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(50) NOT NULL DEFAULT 'medium',
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT status_check CHECK (status IN ('pending', 'in_progress', 'completed')),
    CONSTRAINT priority_check CHECK (priority IN ('low', 'medium', 'high'))
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);

-- Audit log for task changes
CREATE TABLE task_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_task_id ON task_audit_log(task_id);
```

---

## 📦 Phase 1: Foundation & Database Setup

### 1.1 PostgreSQL Setup

**File**: `mcp-server/src/database/__init__.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from ..config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**File**: `mcp-server/src/models/database.py`
```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oauth_sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default="pending")
    priority = Column(String(50), nullable=False, default="medium")
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**File**: `mcp-server/alembic.ini`
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://user:password@localhost:5432/workflow_orchestrator

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Commands**:
```bash
cd mcp-server
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 1.2 Update Configuration

**File**: `mcp-server/src/config.py` (update)
```python
# Database Configuration
database_url: str = "postgresql+asyncpg://user:password@localhost:5432/workflow_orchestrator"
database_pool_size: int = 5
database_max_overflow: int = 10

# Email Configuration (SMTP)
smtp_host: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_user: str
smtp_password: str
smtp_from_email: str
smtp_use_tls: bool = True
```

**File**: `mcp-server/.env.example` (update)
```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/workflow_orchestrator

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
```

---

## 📦 Phase 2: OAuth Authentication (Epic 2)

### 2.1 OAuth Flow Implementation

**File**: `mcp-server/src/auth/oauth.py`
```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.database import User
from ..config import settings
import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/oauth", tags=["auth"])

@router.get("/authorize")
async def authorize(redirect_uri: str):
    """OAuth authorization endpoint."""
    # Generate authorization code
    auth_code = generate_auth_code()

    # Store auth code in Redis with redirect_uri
    await redis.setex(
        f"auth_code:{auth_code}",
        300,  # 5 minutes
        redirect_uri
    )

    # In production, show login/consent screen
    # For MVP, auto-approve
    return RedirectResponse(
        url=f"{redirect_uri}?code={auth_code}"
    )

@router.post("/token")
async def token(
    code: str,
    redirect_uri: str,
    db: AsyncSession = Depends(get_db)
):
    """Exchange authorization code for access token."""
    # Verify auth code
    stored_redirect = await redis.get(f"auth_code:{code}")
    if not stored_redirect or stored_redirect != redirect_uri:
        raise HTTPException(status_code=400, detail="Invalid code")

    # Delete auth code (one-time use)
    await redis.delete(f"auth_code:{code}")

    # Create or get user
    user = await get_or_create_user(db, oauth_sub="test_user")

    # Generate JWT access token
    access_token = jwt.encode(
        {
            "sub": user.oauth_sub,
            "user_id": str(user.id),
            "exp": datetime.utcnow() + timedelta(hours=1)
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }
```

### 2.2 Auth Middleware

**File**: `mcp-server/src/auth/middleware.py`
```python
from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.database import User
import jwt
from ..config import settings

async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate user from JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
```

---

## 📦 Phase 3: MCP Tools Implementation (Epic 3)

### 3.1 Task Management Tools

**File**: `mcp-server/src/tools/tasks.py`
```python
from mcp.types import CallToolResult, TextContent
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.database import Task
from ..models.task import TaskCreate, TaskUpdate
from datetime import datetime
import uuid

async def create_task_tool(arguments: dict, user_id: str, db: AsyncSession) -> CallToolResult:
    """Create a new task - pure business logic, no AI."""

    # Validate and create task
    task_data = TaskCreate(**arguments)

    new_task = Task(
        id=uuid.uuid4(),
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        status="pending"
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Return MCP response with UI component
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"✅ Task created: '{new_task.title}' (Priority: {new_task.priority})"
            )
        ],
        structuredContent={
            "type": "task_created",
            "taskId": str(new_task.id),
            "title": new_task.title,
            "priority": new_task.priority,
            "status": new_task.status
        },
        _meta={
            "ui/resourceUri": "ui://tasks/card",
            "task": {
                "id": str(new_task.id),
                "title": new_task.title,
                "description": new_task.description,
                "status": new_task.status,
                "priority": new_task.priority,
                "dueDate": new_task.due_date.isoformat() if new_task.due_date else None,
                "createdAt": new_task.created_at.isoformat()
            }
        }
    )

async def list_tasks_tool(arguments: dict, user_id: str, db: AsyncSession) -> CallToolResult:
    """List tasks with filters - pure business logic."""

    # Build query with filters
    query = select(Task).where(Task.user_id == user_id)

    if arguments.get("status"):
        query = query.where(Task.status == arguments["status"])

    if arguments.get("priority"):
        query = query.where(Task.priority == arguments["priority"])

    if arguments.get("overdue"):
        query = query.where(
            Task.due_date < datetime.utcnow(),
            Task.status != "completed"
        )

    # Execute query
    result = await db.execute(query.order_by(Task.created_at.desc()))
    tasks = result.scalars().all()

    # Return MCP response with table UI
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Found {len(tasks)} tasks"
            )
        ],
        structuredContent={
            "type": "task_list",
            "count": len(tasks),
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority
                }
                for t in tasks
            ]
        },
        _meta={
            "ui/resourceUri": "ui://tasks/table",
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "dueDate": t.due_date.isoformat() if t.due_date else None,
                    "createdAt": t.created_at.isoformat(),
                    "updatedAt": t.updated_at.isoformat()
                }
                for t in tasks
            ]
        }
    )

async def update_task_status_tool(arguments: dict, user_id: str, db: AsyncSession) -> CallToolResult:
    """Update task status - pure business logic."""

    task_id = arguments["task_id"]
    new_status = arguments["status"]

    # Get task
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise ValueError(f"Task {task_id} not found")

    # Audit log
    old_status = task.status

    # Update status
    task.status = new_status
    task.updated_at = datetime.utcnow()

    await db.commit()

    # Log audit
    audit_log = TaskAuditLog(
        task_id=task.id,
        user_id=user_id,
        action="status_update",
        old_status=old_status,
        new_status=new_status
    )
    db.add(audit_log)
    await db.commit()

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"✅ Task '{task.title}' updated: {old_status} → {new_status}"
            )
        ],
        structuredContent={
            "type": "task_updated",
            "taskId": str(task.id),
            "oldStatus": old_status,
            "newStatus": new_status
        },
        _meta={
            "ui/resourceUri": "ui://tasks/status-update",
            "task": {
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "updatedAt": task.updated_at.isoformat()
            }
        }
    )
```

### 3.2 Email Integration Tool

**File**: `mcp-server/src/tools/integrations.py`
```python
from mcp.types import CallToolResult, TextContent
from ..services.email_service import send_email
from ..config import settings

async def trigger_integration_tool(arguments: dict, user_id: str) -> CallToolResult:
    """Trigger external integration - email only for MVP."""

    integration_type = arguments["integration_type"]
    action = arguments["action"]
    data = arguments.get("data", {})

    if integration_type == "email":
        # Send email via SMTP
        result = await send_email(
            to=data.get("to"),
            subject=data.get("subject"),
            body=data.get("body")
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"✅ Email sent to {data.get('to')}"
                )
            ],
            structuredContent={
                "type": "integration_triggered",
                "integration": "email",
                "status": "success"
            },
            _meta={
                "ui/resourceUri": "ui://integrations/confirmation",
                "details": {
                    "to": data.get("to"),
                    "subject": data.get("subject"),
                    "sentAt": datetime.utcnow().isoformat()
                }
            }
        )
    else:
        raise ValueError(f"Integration '{integration_type}' not supported in MVP")
```

**File**: `mcp-server/src/services/email_service.py`
```python
import aiosmtplib
from email.message import EmailMessage
from ..config import settings

async def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via SMTP - pure business logic, no AI."""

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls
        )
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise
```

---

## 📦 Phase 4: React UI Components

### 4.1 UI Resource Declaration

**File**: `mcp-server/src/ui/resources.py`
```python
from mcp.types import Resource

# Declare UI resources that ChatGPT can render
UI_RESOURCES = [
    Resource(
        uri="ui://tasks/card",
        name="Task Card",
        mimeType="text/html+mcp",
        description="Display a single task as a card"
    ),
    Resource(
        uri="ui://tasks/table",
        name="Task Table",
        mimeType="text/html+mcp",
        description="Display tasks in a sortable table"
    ),
    Resource(
        uri="ui://tasks/status-update",
        name="Status Update Confirmation",
        mimeType="text/html+mcp",
        description="Show task status update confirmation"
    ),
    Resource(
        uri="ui://integrations/confirmation",
        name="Integration Confirmation",
        mimeType="text/html+mcp",
        description="Show integration trigger confirmation"
    )
]

# Register resources with MCP server
@mcp.list_resources()
async def list_resources():
    return UI_RESOURCES
```

### 4.2 React Components

**File**: `ui/src/components/Tasks/TaskCard.tsx`
```typescript
import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface TaskData {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  dueDate?: string;
  createdAt: string;
}

export function TaskCard() {
  const [task, setTask] = useState<TaskData | null>(null);

  useEffect(() => {
    // Access tool metadata from ChatGPT host
    const metadata = (window as any).openai?.toolResponseMetadata;

    if (metadata?._meta?.task) {
      setTask(metadata._meta.task);
    }
  }, []);

  if (!task) return <div>Loading...</div>;

  const priorityColors = {
    high: 'destructive',
    medium: 'default',
    low: 'secondary'
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>{task.title}</span>
          <Badge variant={priorityColors[task.priority as keyof typeof priorityColors]}>
            {task.priority}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {task.description && (
          <p className="text-muted-foreground mb-4">{task.description}</p>
        )}
        <div className="flex gap-2">
          <Badge variant="outline">{task.status}</Badge>
          {task.dueDate && (
            <span className="text-sm text-muted-foreground">
              Due: {new Date(task.dueDate).toLocaleDateString()}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

**File**: `ui/src/components/Tasks/TaskTable.tsx`
```typescript
import { useEffect, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string;
  dueDate?: string;
}

export function TaskTable() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const metadata = (window as any).openai?.toolResponseMetadata;

    if (metadata?._meta?.tasks) {
      setTasks(metadata._meta.tasks);
    }
  }, []);

  const handleStatusUpdate = async (taskId: string, newStatus: string) => {
    // Call MCP tool via ChatGPT host
    await (window as any).openai?.callTool('update_task_status', {
      task_id: taskId,
      status: newStatus
    });
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead>Due Date</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow key={task.id}>
            <TableCell className="font-medium">{task.title}</TableCell>
            <TableCell>
              <Badge variant="outline">{task.status}</Badge>
            </TableCell>
            <TableCell>
              <Badge>{task.priority}</Badge>
            </TableCell>
            <TableCell>
              {task.dueDate ? new Date(task.dueDate).toLocaleDateString() : '-'}
            </TableCell>
            <TableCell>
              <div className="flex gap-2">
                {task.status !== 'completed' && (
                  <Button
                    size="sm"
                    onClick={() => handleStatusUpdate(task.id, 'completed')}
                  >
                    Complete
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

---

## 🐳 Phase 5: Docker & Deployment

### 5.1 Docker Compose (Local Development)

**File**: `docker-compose.yml` (update)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: workflow-orchestrator-postgres
    environment:
      POSTGRES_USER: workflow_user
      POSTGRES_PASSWORD: workflow_password
      POSTGRES_DB: workflow_orchestrator
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U workflow_user"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: workflow-orchestrator-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mcp-server:
    build:
      context: ./mcp-server
      dockerfile: ../docker/Dockerfile.mcp-server
    container_name: workflow-orchestrator-mcp
    ports:
      - "8000:8000"
    env_file:
      - ./mcp-server/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./mcp-server:/app
      - /app/.venv
    command: uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

  ui:
    build:
      context: ./ui
      dockerfile: ../docker/Dockerfile.ui
    container_name: workflow-orchestrator-ui
    ports:
      - "3000:3000"
    env_file:
      - ./ui/.env
    volumes:
      - ./ui:/app
      - /app/node_modules
    command: npm run dev -- --host
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 5.2 Production Dockerfile

**File**: `docker/Dockerfile.mcp-server` (update)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Run database migrations on startup
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File**: `docker/docker-entrypoint.sh`
```bash
#!/bin/bash
set -e

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL ready"

# Run migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Start application
exec "$@"
```

### 5.3 VPS Deployment (Ubuntu)

**File**: `deploy/docker-compose.prod.yml`
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - backend

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - backend

  mcp-server:
    image: ghcr.io/your-username/workflow-orchestrator-mcp:latest
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
    depends_on:
      - postgres
      - redis
    restart: always
    networks:
      - backend
      - frontend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - mcp-server
    restart: always
    networks:
      - frontend

networks:
  backend:
  frontend:

volumes:
  postgres_data:
  redis_data:
```

---

## 🧪 Testing Strategy

### Unit Tests

**File**: `mcp-server/tests/test_tasks.py`
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.tools.tasks import create_task_tool, list_tasks_tool

@pytest.mark.asyncio
async def test_create_task(db: AsyncSession):
    result = await create_task_tool(
        arguments={
            "title": "Test task",
            "priority": "high"
        },
        user_id="test-user-123",
        db=db
    )

    assert result.structuredContent["type"] == "task_created"
    assert result.structuredContent["title"] == "Test task"
    assert result._meta["ui/resourceUri"] == "ui://tasks/card"

@pytest.mark.asyncio
async def test_list_tasks_with_filter(db: AsyncSession):
    # Create tasks
    await create_task_tool(
        {"title": "Task 1", "status": "pending"},
        "test-user-123",
        db
    )
    await create_task_tool(
        {"title": "Task 2", "status": "completed"},
        "test-user-123",
        db
    )

    # List only pending
    result = await list_tasks_tool(
        {"status": "pending"},
        "test-user-123",
        db
    )

    assert result.structuredContent["count"] == 1
    assert result._meta["tasks"][0]["title"] == "Task 1"
```

### Integration Tests

```bash
# Run all tests
cd mcp-server
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

---

## 📋 Implementation Checklist

### Phase 1: Foundation ✅
- [ ] Set up PostgreSQL database
- [ ] Create Alembic migrations
- [ ] Implement database models
- [ ] Set up async SQLAlchemy session
- [ ] Update config for PostgreSQL
- [ ] Test database connection

### Phase 2: Authentication ✅
- [ ] Implement OAuth authorize endpoint
- [ ] Implement OAuth token endpoint
- [ ] Create JWT token generation
- [ ] Implement auth middleware
- [ ] Test OAuth flow end-to-end
- [ ] Store user sessions in Redis

### Phase 3: MCP Tools ✅
- [ ] Implement `create_task` tool
- [ ] Implement `list_tasks` tool
- [ ] Implement `update_task_status` tool
- [ ] Implement `trigger_integration` (email)
- [ ] Create email service with SMTP
- [ ] Add audit logging
- [ ] Write unit tests for all tools

### Phase 4: UI Components ✅
- [ ] Declare UI resources in MCP server
- [ ] Create TaskCard React component
- [ ] Create TaskTable React component
- [ ] Create StatusUpdate component
- [ ] Test UI rendering in local environment
- [ ] Implement `window.openai` API integration

### Phase 5: Docker & Deployment ✅
- [ ] Update Docker Compose for PostgreSQL
- [ ] Create production Dockerfile
- [ ] Create docker-entrypoint.sh for migrations
- [ ] Set up nginx configuration
- [ ] Configure SSL certificates
- [ ] Deploy to VPS
- [ ] Test production deployment

---

## 🚀 Next Steps (Phase 2)

After MVP completion:
1. **Epic 4**: Reporting & Analytics
2. **Epic 5**: Jira/Slack integrations
3. **Epic 6**: Advanced UX (confirmations, error states)
4. **Epic 7**: Security hardening, rate limiting
5. **Epic 8**: OpenAI app submission

---

## 📚 Reference Documentation

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [ChatGPT Apps UI Guide](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/)
