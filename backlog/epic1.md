🧭 EPIC 1 — ChatGPT App Foundation & Compliance

Goal: Ensure the app fully complies with OpenAI ChatGPT Apps requirements and can be loaded, invoked, and rendered inside ChatGPT.

User Story 1.1 — MCP Server Bootstrapping

As a ChatGPT App
I want a publicly accessible MCP server
So that ChatGPT can discover and call its tools

Acceptance Criteria
	•	MCP server exposes /mcp endpoint over HTTPS
	•	Server responds with valid MCP manifest
	•	Tools are discoverable by ChatGPT
	•	Health check endpoint returns 200

⸻

User Story 1.2 — Tool Schema Definition

As a ChatGPT client
I want strongly typed tool schemas
So that user intent can be reliably mapped to backend actions

Acceptance Criteria
	•	Each tool has:
	•	Name
	•	Description
	•	JSON input schema
	•	Deterministic output schema
	•	Schemas validated against MCP spec
	•	No ambiguous parameters

⸻

User Story 1.3 — ChatGPT UI Rendering Compatibility

As a user
I want responses rendered as structured UI components
So that results are actionable, not just text

Acceptance Criteria
	•	MCP responses include UI metadata
	•	Tables, buttons, and status badges render correctly
	•	UI degrades gracefully to text if rendering fails

---

Progress Notes (2026-01-03)
- UI resource registered with `text/html+skybridge` and widget metadata (CSP, description, border preference).
- Tool metadata includes `openai/outputTemplate` and invocation messaging for widget rendering.
- Tool responses now keep structuredContent concise and pass full UI payload via `_meta` for widgets.

