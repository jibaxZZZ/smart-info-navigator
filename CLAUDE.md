# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workflow Orchestrator** is a ChatGPT App that executes real business logic and workflows through natural language commands.

**CRITICAL**: This backend performs **NO AI/LLM calls** - it's pure business logic (CRUD operations, integrations, workflows). ChatGPT acts only as the MCP client for natural language interface.

### Key Capabilities
- Task management (create, list, update tasks)
- Report generation (KPIs, productivity metrics)
- Workflow scheduling and automation
- External system integrations (Jira, Email, Slack)
- Interactive UI components in ChatGPT

### Target Users
- Project managers automating task workflows
- Operations specialists generating reports conversationally
- IT administrators orchestrating system actions

## Architecture

### Technology Stack

**MCP Server (Python) - Business Logic Only**
- **MCP Python SDK** - Model Context Protocol server
- **UV** - Package manager
- **FastAPI** - REST endpoints for OAuth
- **SQLAlchemy** - Database ORM for tasks/workflows
- **Redis** - Session management and caching
- **OAuth 2.0** - Required by ChatGPT

**NO AI/LLM Dependencies**: No OpenAI, no Anthropic, no LLM calls. Pure business logic.

**Frontend (React)**
- **React + TypeScript** - Interactive UI components
- **ShadCN UI + Tailwind** - Component library
- **Tables, buttons, filters** - Task management UI

**Communication Flow**
```
ChatGPT (natural language) → MCP Protocol → Python Server (business logic) → Database/APIs
                                          ↓
                                   React UI Components (rendered in ChatGPT)
```

### Project Structure

```
smart-info-navigator/
├── .github/
│   └── workflows/           # CI/CD workflows (future)
├── mcp-server/              # Python MCP server
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py          # MCP server entry point
│   │   ├── config.py        # Configuration management
│   │   ├── auth/            # OAuth 2.0 implementation
│   │   ├── tools/           # MCP tool implementations
│   │   │   ├── analyze_text.py
│   │   │   ├── checklist.py
│   │   │   ├── export.py
│   │   │   └── base.py
│   │   ├── services/        # Business logic services
│   │   │   ├── ai_service.py
│   │   │   ├── session_service.py
│   │   │   └── export_service.py
│   │   ├── models/          # Pydantic data models
│   │   │   ├── summary.py
│   │   │   ├── checklist.py
│   │   │   └── response.py
│   │   └── utils/           # Utility functions
│   ├── tests/               # pytest tests
│   ├── pyproject.toml       # UV package configuration
│   ├── .env.example         # Environment template
│   └── README.md
├── ui/                      # React frontend
│   ├── public/
│   ├── src/
│   │   ├── main.tsx         # App entry point
│   │   ├── App.tsx          # Root component
│   │   ├── components/
│   │   │   ├── ui/          # ShadCN UI components
│   │   │   ├── Summary/     # Summary view components
│   │   │   ├── Checklist/   # Checklist components
│   │   │   ├── Export/      # Export panel
│   │   │   └── Layout/      # Layout components
│   │   ├── hooks/           # Custom React hooks
│   │   │   ├── useMCP.ts
│   │   │   ├── useChecklist.ts
│   │   │   └── useExport.ts
│   │   ├── stores/          # Zustand state stores
│   │   ├── types/           # TypeScript definitions
│   │   ├── lib/             # Utilities and MCP client
│   │   └── styles/          # Global CSS
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── components.json      # ShadCN configuration
│   └── .env.example
├── docker/
│   ├── Dockerfile.mcp-server
│   ├── Dockerfile.ui
│   └── nginx.conf (future)
├── docker-compose.yml       # Local development setup
├── .gitignore
├── .env.example
├── CLAUDE.md
├── prd-smart-info-navigator.md
├── README.md
└── LICENSE
```

### Core Components to Implement

1. **MCP Server (Python) - Business Logic**
   - OAuth 2.0 authentication handler
   - Database models (Task, Workflow, Report)
   - CRUD operations for tasks
   - Report generation (KPIs calculation)
   - Workflow scheduler
   - External API integrations (Jira, Email, Slack)

2. **React UI Components**
   - Task table with filters and sorting
   - Task creation/edit forms
   - Status update buttons
   - Report dashboards (charts, metrics)
   - Workflow scheduler interface
   - Integration status indicators

3. **MCP Tools (No AI - Pure Business Logic)**
   - `create_task` - Add task to database
   - `list_tasks` - Query tasks with filters
   - `update_task_status` - Update task state
   - `generate_report` - Calculate KPIs from data
   - `trigger_integration` - Call external APIs
   - `schedule_workflow` - Plan automated actions

### Development Commands

**Python MCP Server**
```bash
# Install dependencies
uv sync

# Run MCP server in development
uv run python -m mcp_server

# Run tests
uv run pytest

# Type checking
uv run mypy src/
```

**React UI**
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

### Authentication Setup

The MCP server must implement OAuth flow as required by ChatGPT Apps:
- OAuth 2.0 authorization endpoint
- Token exchange mechanism
- Secure token storage and validation
- Session management with authenticated users

### Performance & Reliability Requirements

- **Response time**: <3 seconds for text analysis operations
- **Uptime target**: ≥99% availability
- **Session persistence**: Maintain history within user session (FR6)
- **Error handling**: Graceful degradation with user-friendly messages

### MCP Server Considerations

**Tool Design**
- Each MCP tool should be atomic and focused
- Return structured data (JSON) for React components to render
- Include progress indicators for long-running operations
- Support streaming responses for large text analysis

**State Management**
- Maintain per-session state for checklist items
- Track user interactions (checked items, filters applied)
- Cache analysis results to improve performance

**Security**
- Validate OAuth tokens on every request
- Sanitize user input to prevent injection attacks
- Rate limiting to prevent abuse
- Secure handling of exported files

## UX Principles

- **Immediate clarity** - clear headings, segmented output
- **Interactive actions** - buttons, checkboxes, simple controls
- **Visual structure** - hierarchy and spacing for easy scanning
- **Feedback** - visual cues after actions (e.g., export complete)

## Key Implementation Patterns

### Data Flow

1. **User Input → Analysis**
   ```
   ChatGPT UI → MCP analyze_text → Python processing → Structured JSON response
   ```

2. **Checklist Interaction**
   ```
   React UI (checkbox click) → MCP update_checklist_item → Session state update → UI refresh
   ```

3. **Export Flow**
   ```
   User action → MCP export_content → Generate file → Return download link
   ```

### React Component Structure

```typescript
// Example structure for interactive components
interface ChecklistItem {
  id: string;
  content: string;
  completed: boolean;
  priority?: 'high' | 'medium' | 'low';
}

interface Summary {
  title: string;
  sections: Section[];
  metadata: { wordCount: number; readTime: string };
}
```

### MCP Tool Response Format

All MCP tools should return consistent JSON structures:
```python
{
  "success": bool,
  "data": {...},  # Tool-specific payload
  "metadata": {
    "timestamp": str,
    "processingTime": float
  },
  "error": Optional[str]
}
```

## Success Metrics to Consider

- Usage rate: % of users generating at least one checklist per session
- Checklist completion rate: % of checklists actively completed
- Response time: average <3 seconds for text analysis
- UX satisfaction: average ≥4/5 rating

## Getting Started

### Initial Setup

1. **Install dependencies**:
   ```bash
   # MCP Server
   cd mcp-server
   uv sync

   # React UI
   cd ../ui
   npm install
   ```

2. **Configure environment**:
   ```bash
   # Copy and edit environment files
   cp mcp-server/.env.example mcp-server/.env
   cp ui/.env.example ui/.env
   # Add your OpenAI API key and OAuth credentials
   ```

3. **Run with Docker Compose** (recommended):
   ```bash
   docker-compose up
   ```
   OR run services manually:
   ```bash
   # Terminal 1: Redis
   redis-server

   # Terminal 2: MCP Server
   cd mcp-server && uv run python -m src.main

   # Terminal 3: React UI
   cd ui && npm run dev
   ```

### When Implementing New Features

1. Define the MCP tool in `mcp-server/src/tools/`
2. Implement the business logic with proper error handling
3. Create corresponding React components in `ui/src/components/`
4. Test the OAuth flow and MCP communication
5. Verify UI renders correctly within ChatGPT interface

### Current Implementation Status

**Completed (2026-01-04)**:
- ✅ Project structure created
- ✅ MCP server foundation (config, models, main.py)
- ✅ React UI foundation (Vite, TypeScript, ShadCN setup)
- ✅ Docker Compose configuration
- ✅ Environment configuration templates
- ✅ **OAuth 2.0 authentication flow** (PKCE, JWT, database-backed)
- ✅ **OAuth endpoints** (/authorize, /token, /revoke, /register, /.well-known/*)
- ✅ **OAuth middleware** for protecting MCP endpoints
- ✅ **Database migrations** for OAuth tables (clients, codes, tokens)
- ✅ **MCP client library** in React with TypeScript (mcp-client.ts)
- ✅ **App.tsx wired** with real components, React Query, and MCP client
- ✅ **Task management tools** (create_task, list_tasks, update_task_status)
- ✅ **Email integration** (Gmail SMTP working)
- ✅ **Unit tests** for OAuth endpoints (pytest)
- ✅ **Postman collection** for OAuth flow testing

**To Implement (Phase 2)**:
- ⏳ Report generation service (generate_report)
- ⏳ Workflow scheduling (schedule_workflow)
- ⏳ Jira integration
- ⏳ Slack integration
- ⏳ Export service (PDF, Markdown, CSV)
- ⏳ Consent screen UI for OAuth authorization
- ⏳ Real user authentication (replace mock user)
- ⏳ JWKS endpoint implementation for RS256
- ⏳ Rate limiting middleware
- ⏳ Prometheus metrics

## Reference Documents

- **PRD**: `prd-smart-info-navigator.md` - Complete product requirements and functional specifications
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **UV Documentation**: https://github.com/astral-sh/uv
