# Smart Info Navigator - MCP Server

MCP (Model Context Protocol) server for Smart Info Navigator ChatGPT App.

## Setup

### Prerequisites

- Python 3.11+
- UV package manager
- Redis server

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys and configuration.

### Development

Run the MCP server:
```bash
uv run python -m src.main
```

Run tests:
```bash
uv run pytest
```

Type checking:
```bash
uv run mypy src/
```

Code formatting:
```bash
uv run black src/
uv run ruff check src/
```

## MCP Tools

### analyze_text
Analyzes raw text and returns structured summary with sections.

**Input:**
- `text` (string): Raw text to analyze

**Output:**
- Summary object with title, sections, and metadata

### generate_checklist
Generates actionable checklist from text or summary.

**Input:**
- `source` (string): Source text or summary ID
- `title` (string, optional): Checklist title

**Output:**
- Checklist object with items and priorities

### update_checklist_item
Updates checklist item completion status.

**Input:**
- `checklist_id` (string): Checklist identifier
- `item_id` (string): Item identifier
- `completed` (boolean): New completion status

**Output:**
- Updated checklist object

### export_content
Exports summary or checklist to PDF, Markdown, or CSV.

**Input:**
- `content_id` (string): Summary or checklist ID
- `format` (string): Export format (pdf, markdown, csv)

**Output:**
- Download URL or base64-encoded file

## Architecture

```
src/
├── main.py              # MCP server entry point
├── config.py            # Configuration management
├── auth/                # OAuth implementation
├── tools/               # MCP tool implementations
├── services/            # Business logic services
├── models/              # Pydantic data models
└── utils/               # Utility functions
```

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `OPENAI_API_KEY`: OpenAI API key for text analysis
- `REDIS_URL`: Redis connection URL
- `OAUTH_CLIENT_ID`: OAuth client ID
- `OAUTH_CLIENT_SECRET`: OAuth client secret
- `JWT_SECRET`: JWT signing secret
