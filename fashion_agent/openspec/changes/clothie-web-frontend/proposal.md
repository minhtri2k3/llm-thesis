# Proposal: Clothie Web Frontend

## Summary

Build a Flutter Web application ("Clothie") that acts as the public-facing chat interface for the Fashion Agent RAG backend. The app will be served via a dedicated Nginx Docker container, exposed publicly through a Cloudflare tunnel ("llm-thesis"), and will communicate with the FastAPI backend through Nginx reverse proxy (so the Flutter JS uses only relative URLs).

## Problem

The current backend has a working RAG pipeline + Gradio UI, but Gradio is primarily a dev/research tool — not suitable for user studies or thesis evaluations. We need a polished, public-facing interface to:
1. Collect user names per session (for tracking)
2. Let users chat with the fashion agent using streamed SSE responses
3. Collect structured ratings and feedback post-session

## Goals

- **4-screen Flutter Web app**: Splash → Register → Chat → Rating
- **SSE streaming**: Real-time token rendering matching the speed of the Gemini backend
- **Thinking status**: Visual indicator for the agent's reasoning phase
- **Product cards**: Render fashion item images inline in chat
- **Evaluation data**: Store `user_name` and `user_ratings` in PostgreSQL for thesis analysis
- **Publicly accessible**: Cloudflare tunnel "llm-thesis" → Nginx → Flutter + API proxy
- **Docker-first**: Separate `clothie-web` service in `fashion_agent/docker-compose.yml`

## Non-Goals

- Mobile app (web only)
- Authentication / login (just a name field)
- Admin dashboard
- Multi-language support

## Scope

### Backend (fashion_agent)
- Add `POST /api/sessions` endpoint (create session + store `user_name`)
- Add `POST /api/rating` endpoint (store 1-10 stars + feedback text)
- DB: add `user_name` column to `user_sessions`, add `user_ratings` table
- Update `init_memory_tables()` to include new DDL
- Remove old `cloudflared` service from `docker-compose.yml`

### Frontend (clothie_web at llm-thesis/clothie_web/)
- Flutter Web project (4 screens)
- `services/api_service.dart`: REST + SSE client using `package:http`
- Nginx config with `/api/*` reverse proxy to `fashion-api:8000`
- Multi-stage Dockerfile: `ghcr.io/cirruslabs/flutter` builder → `nginx:alpine`
- `docker-compose.yml` addition: `clothie-web` + `cloudflared-fe` services

## Architecture Decision

**Nginx reverse proxy** pattern chosen over separate public BE URL because:
- Flutter JS uses relative `/api/...` URLs → no hardcoded hostnames
- No CORS issues (same origin)
- SSE works through Nginx with `proxy_buffering off`
- One Cloudflare tunnel manages the entire product
- `clothie-web` container joins `internal` Docker network to resolve `fashion-api`

## Success Criteria

- [ ] Any user can open the Cloudflare public URL and complete a full session
- [ ] SSE tokens render progressively in the browser (not batched)
- [ ] Thinking animation appears during agent reasoning phase
- [ ] User name and rating are stored in PostgreSQL after session
- [ ] `docker compose up -d` in `fashion_agent/` starts everything including FE
