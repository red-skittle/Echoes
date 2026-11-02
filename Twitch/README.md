# Echoes

**Every streamer has a story. Make it searchable.**

Echoes is a video-first, community-maintained encyclopedia for Twitch. The MVP has persistent wiki/video/source records, creator OAuth, public VOD metadata import, authorized uploads, source-grounded search, community contributions, and explicit synthetic sample content. Sample entries and timestamps do not represent real broadcasts and are not playable media.

## Run locally

Requirements: Node.js 20+ and Python 3.11+. SQLite is the zero-setup development database. Docker Compose supplies PostgreSQL with pgvector and Redis for deployments.

```powershell
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

In a second terminal, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The web app is at `http://localhost:3000`, the API at `http://localhost:8000`, and interactive API docs at `/docs`. The default SQLite database is `./afterlife.db` in the API process working directory.

For Twitch login, configure `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `TWITCH_REDIRECT_URI`, and a unique `SESSION_SECRET` in the backend environment. Register that exact callback URL with your Twitch app. OAuth and Helix calls are implemented but were not exercised against Twitch because no credentials were provided.

For PostgreSQL and Redis, run `docker compose up -d`, set `DATABASE_URL=postgresql+psycopg://afterlife:afterlife@localhost:5432/afterlife` and `REDIS_URL` in the backend environment, then run `alembic -c alembic.ini upgrade head` from `backend`. Docker was unavailable in the inspected environment, so PostgreSQL runtime behavior remains unverified.

On Windows ARM, if Next.js reports that it cannot load SWC, run this in the same shell before `npm.cmd run dev`:

```powershell
$env:NEXT_TEST_WASM_DIR = (Resolve-Path 'node_modules/@next/swc-wasm-nodejs').Path
```

## What works

- Explore and streamer wiki pages, source-linked articles, video records, dashboard, settings, and contribution pages.
- Public Twitch VOD metadata import through Helix. It stores metadata only and does not download video media.
- Twitch OAuth with state validation, Twitch profile verification, and signed HttpOnly sessions. Access tokens are not sent to the browser or persisted.
- Creator-owned upload, checked against the authenticated Twitch owner membership, capped by `MAX_UPLOAD_SIZE_MB`, stored using generated file names, and deduplicated by SHA-256.
- When FFmpeg and `OPENAI_API_KEY` are configured, the processing route extracts ten-minute audio chunks, transcribes timed segments, validates structured event drafts, stores source timestamps/topics/entities/relationships, and generates embeddings. AI entries remain `pending_review`.
- Grounded search uses OpenAI embeddings when indexed vectors exist. PostgreSQL ranks with pgvector cosine distance; SQLite computes cosine similarity in the API. Without configured embeddings, search uses local keyword matching. Answers are summaries from retrieved entries with their sources, never freeform generated claims.
- Contribution submissions can be reviewed using a server-configured `AFTERLIFE_REVIEW_TOKEN`; the reviewer token is held only in the current browser session.
- SQLAlchemy models and Alembic migrations cover users, streamer memberships, videos, assets, transcripts, timed segments, wiki entries/sources, topics, entities, relationships, embeddings, contributions, and jobs.
- Synthetic seed data: one sample streamer, three metadata-only sample videos, twelve sample wiki entries. These records are labeled and not derived from real Twitch streams.

## Known limits

- No Twitch or OpenAI credentials were provided, and FFmpeg is not installed in the inspected environment. OAuth, imports, actual transcription, and LLM extraction have not been exercised here. No real media has been processed.
- Processing runs in FastAPI in-process background tasks. It is not a durable Redis worker; jobs interrupted by a server restart need recovery. Uploads use local disk rather than object storage.
- Review authorization uses a shared token instead of per-user moderator roles. Production rate limiting, malware scanning, object storage, upload quotas, and detailed owner/moderator permissions need work before public deployment.
- The supplied Docker Compose services were not run because Docker is unavailable in this environment.

## Configuration and media permissions

Copy `.env.example` to `.env`. Keep real keys out of source control. `NEXT_PUBLIC_API_URL` is browser-visible; Twitch and OpenAI credentials belong only in the backend environment. Twitch VOD metadata does not grant access to raw media. Only creator-authorized uploads or accessible media supplied by the creator may be processed.
