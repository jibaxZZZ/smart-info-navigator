# Workflow Orchestrator

A ChatGPT App that executes real business logic and workflows through natural language commands. This backend performs **NO AI/LLM calls** - it's pure business logic (CRUD operations, integrations, workflows). ChatGPT acts only as the MCP client for natural language interface.

## Features

- **Task Management**: Create, list, update, and track tasks with filters and priorities
- **Email Notifications**: Send automated email notifications via Gmail SMTP
- **Workflow Automation**: Schedule and execute business workflows
- **Report Generation**: Generate productivity reports and KPIs from task data
- **ChatGPT Integration**: Seamless integration with ChatGPT via MCP protocol
- **OAuth 2.0 Authentication**: Secure user authentication with Auth0

## Architecture

```
workflow-orchestrator/
├── mcp-server/          # Python MCP server (FastAPI + MCP SDK)
├── ui/                  # React UI (Vite + TypeScript + ShadCN)
├── docker/              # Docker configurations
└── docker-compose.yml   # Local development setup
```

### Tech Stack

**Backend (MCP Server) - Pure Business Logic**
- Python 3.11+ with MCP SDK
- UV for package management
- FastAPI for OAuth and REST endpoints
- PostgreSQL for data persistence
- Redis for session management
- Auth0 for OAuth 2.0 authentication
- Gmail SMTP for email notifications
- **NO AI/LLM calls** - pure business logic only

**Frontend**
- Vite + React 18 + TypeScript
- ShadCN UI + Tailwind CSS
- Zustand for state management
- React Query for server state

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- UV package manager (`pip install uv`)
- Docker and Docker Compose

### Local Development with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd smart-info-navigator
```

2. Copy environment files:
```bash
cp mcp-server/.env.example mcp-server/.env
cp ui/.env.example ui/.env
```

3. Edit `.env` files and add your credentials:
   - `mcp-server/.env`: Add your Auth0 credentials, Gmail SMTP credentials, and JWT secret
   - `ui/.env`: Configure API endpoints

4. Start all services with Docker Compose:
```bash
docker-compose up
```

Services will be available at:
- MCP Server: http://localhost:8000
- React UI: http://localhost:3000
- PostgreSQL: localhost:5433 (Docker container, avoids conflict with local port 5432)
- Redis: localhost:6380 (Docker container, avoids conflict with local port 6379)

### Manual Setup

#### MCP Server

```bash
cd mcp-server
cp .env.example .env
# Edit .env with your configuration
uv sync
uv run python -m src.main
```

#### React UI

```bash
cd ui
cp .env.example .env
# Edit .env with your configuration
npm install
npm run dev
```

## Development

### MCP Server

```bash
cd mcp-server

# Install dependencies
uv sync

# Run server
uv run python -m src.main

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Code formatting
uv run black src/
uv run ruff check src/
```

### React UI

```bash
cd ui

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

## MCP Tools

The server exposes the following MCP tools for workflow orchestration (pure business logic, no AI):

- `create_task`: Create a new task in the database
- `list_tasks`: List tasks with filters (status, priority, overdue)
- `update_task_status`: Update task status and log audit trail
- `generate_report`: Generate business reports from task data (KPIs, productivity metrics)
- `trigger_integration`: Trigger external integrations (email notifications via Gmail SMTP)
- `schedule_workflow`: Schedule automated workflows for later execution

## Project Structure

```
smart-info-navigator/
├── mcp-server/
│   ├── src/
│   │   ├── main.py              # MCP server entry point
│   │   ├── config.py            # Configuration
│   │   ├── auth/                # OAuth implementation
│   │   ├── tools/               # MCP tool implementations
│   │   ├── services/            # Business logic
│   │   ├── models/              # Pydantic models
│   │   └── utils/               # Utilities
│   ├── tests/                   # Tests
│   └── pyproject.toml           # UV configuration
├── ui/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   ├── lib/                 # Utilities and MCP client
│   │   ├── stores/              # Zustand stores
│   │   └── types/               # TypeScript types
│   └── package.json
└── docker/                      # Dockerfiles
```

## Configuration

### Environment Variables

**MCP Server** (`mcp-server/.env`)
- `DATABASE_URL`: PostgreSQL connection URL (port 5433 to avoid local conflicts)
- `REDIS_URL`: Redis connection URL (port 6380 to avoid local conflicts)
- `OAUTH_CLIENT_ID`: Auth0 client ID (required)
- `OAUTH_CLIENT_SECRET`: Auth0 client secret (required)
- `JWT_SECRET`: JWT signing secret (required - min 32 chars)
- `SMTP_USER`: Gmail email address (required)
- `SMTP_PASSWORD`: Gmail app-specific password (required)
- `SMTP_FROM_EMAIL`: Email sender address (required)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Log format (json for production, text for development)
- `LOG_OUTPUT`: Log output destination (stdout, file, both)

**React UI** (`ui/.env`)
- `VITE_MCP_SERVER_URL`: MCP server URL
- `VITE_API_BASE_URL`: API base URL

See `.env.example` files in each directory for all available options.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## Documentation

- [PRD](prd-smart-info-navigator.md) - Product Requirements Document
- [CLAUDE.md](CLAUDE.md) - Developer guide for Claude Code
- [MCP Server README](mcp-server/README.md) - Backend documentation
