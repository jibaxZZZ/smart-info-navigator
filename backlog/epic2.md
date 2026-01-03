🔐 EPIC 2 — Authentication & User Identity

Goal: Securely identify users and scope actions to their data.

User Story 2.1 — OAuth Authentication Flow

As a user
I want to authenticate when launching the app
So that my actions are tied to my account

Acceptance Criteria
	•	OAuth 2.0 / OIDC flow supported
	•	Token exchange handled server-side
	•	Access token validated on every MCP call
	•	Unauthorized calls are rejected

⸻

User Story 2.2 — Session & Identity Management

As a backend
I want to identify the current user for each tool call
So that business logic is scoped correctly

Acceptance Criteria
	•	User ID resolved from token
	•	Session context injected into all tools
	•	No cross-user data leakage
	•	Token expiration handled gracefully