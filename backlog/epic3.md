🧰 EPIC 3 — Core Workflow Tools (Business Logic Only)

Goal: Deliver real operational value without any AI on the backend.

⸻

User Story 3.1 — Create Task

As a user
I want to create tasks via natural language
So that I don’t need a dedicated UI or tool

Tool: create_task

Acceptance Criteria
	•	Required fields validated (title, due date, priority)
	•	Task persisted in database
	•	Response returns task card UI
	•	Idempotent behavior supported

⸻

User Story 3.2 — List & Filter Tasks

As a user
I want to list my tasks with filters
So that I can understand my workload quickly

Tool: list_tasks

Acceptance Criteria
	•	Filters: status, due date, priority
	•	Sort options supported
	•	Results rendered as table UI
	•	Pagination supported for large datasets

⸻

User Story 3.3 — Update Task Status

As a user
I want to update task states
So that I can manage progress conversationally

Tool: update_task_status

Acceptance Criteria
	•	Valid state transitions enforced
	•	Audit log recorded
	•	UI updates reflect new status
	•	Error state shown if update fails