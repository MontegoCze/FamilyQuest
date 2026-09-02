# FamilyQuest architecture

## Phase 1 overview

This phase establishes the project skeleton, core database schema, and JWT authentication flow.

## Directory structure

- `backend/` – FastAPI web API
- `database/` – Alembic migration configuration and relational schema definition
- `frontend/` – React + TypeScript UI starter
- `docs/` – architecture, design, and implementation notes

## Design principles

- Secure API access via JWT
- Family membership modeled through `family_members`
- Single source of truth for user-to-family relationships
- Environment-driven configuration for secrets and database access
- SQLite by default for local development, PostgreSQL-ready for production

## Follow-up phases

- Family management and child onboarding
- Tasks and assignments
- Completion and ratings
- XP, levels, achievements, rewards, notifications
- Responsive UI and production hardening
