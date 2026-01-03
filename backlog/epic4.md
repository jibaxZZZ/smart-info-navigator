📊 EPIC 4 — Reporting & Computation (No AI)

Goal: Provide value through deterministic computation, not inference.

User Story 4.1 — Generate Business Report

As a user
I want to generate operational reports
So that I can track performance without spreadsheets

Tool: generate_report

Acceptance Criteria
	•	KPIs computed server-side
	•	Time ranges supported
	•	Results returned as tables and charts
	•	No LLM calls involved

⸻

User Story 4.2 — Export Report

As a user
I want to export reports
So that I can share or archive results

Acceptance Criteria
	•	Export formats: CSV, JSON
	•	Download triggered via UI button
	•	Export respects user permissions