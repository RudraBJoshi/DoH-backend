# UESL Backend — Flask API Server

> **Unified Esports League** — Python/Flask backend powering the UESL platform.

This is the Flask REST API server for UESL. It provides authentication, user management, AI chat (Groq + Gemini), game scoring, social features (friends, presence, microblog), multiplayer Socket.IO, classroom management, and KASM virtual desktop integration.

- **API base**: `https://uesl.opencodingsociety.com`
- **Local dev port**: `8424`
- **Socket.IO port**: `8501` (separate Docker service)
- **Frontend repo**: [MalwareMadness](https://github.com/unified-esports-league/MalwareMadness) — Jekyll + GitHub Pages
- **Live site**: https://ueslhub.opencodingsociety.com

---

## Project Status & Roadmap

### What's Built and Working

| Feature | File | Status |
|---|---|---|
| JWT auth (HS256, 12 hr cookie) | `api/authorize.py`, `api/user.py` | ✅ Working |
| OTP login (6-digit SMTP, 10-min TTL) | `api/otp_api.py` | ✅ Working |
| Google OAuth login | `api/user.py` → `POST /google-login` | ✅ Working |
| Game save/load/delete (upsert by name) | `api/game_api.py` | ✅ Working |
| Community game gallery (public) | `GET /api/game/shared` | ✅ Working |
| Per-game leaderboard (best-score-only) | `api/game_social_api.py` | ✅ Working |
| Game comments (500 char limit, owner/admin delete) | `api/game_social_api.py` | ✅ Working |
| 2-player co-op WebSocket rooms | `api/multiplayer.py` | ✅ Working |
| Live leaderboard Socket.IO server | `socket/socket_server.py` (port 8501) | ✅ Working |
| UESLCoach taunts (Gemini 2.5 Flash) | `api/gemini_api.py` → `POST /api/gemini` | ✅ Working |
| AI NPC dialogue (Gemini 2.5 Flash) | `api/api_ainpc.py` → `POST /api/ainpc/chat` | ✅ Working |
| General AI chat (Groq LLaMA 3.3-70b) | `api/groq_api.py` → `POST /api/groq/chat` | ✅ Working |
| Friends + presence heartbeat | `api/friendship_api.py`, `api/presence_api.py` | ✅ Working |
| DMs with image attachments | `api/social_api.py` → `GET/POST /api/messages/<uid>` | ✅ Working |
| Profile pictures (base64, stored in User row) | `api/pfp.py` | ✅ Working |
| Docker Compose deployment (web + socketio) | `docker-compose.yml` | ✅ Working |

### Key Architecture Notes

- **Two processes in production**: `web` (Flask/SocketIO, port 8424) and `socketio` (standalone leaderboard, port 8501). Both defined in `docker-compose.yml`.
- **Database**: SQLite in dev (`instance/volumes/user_management.db`), MySQL on AWS RDS in prod. Toggle with `IS_PRODUCTION` env var.
- **Auth flow**: every protected endpoint uses `@token_required(role)` from `api/authorize.py`. Checks JWT cookie → Bearer header → Flask-Login session, in that order.
- **OTP store is in-memory** (`_otp_store` dict in `api/otp_api.py`) — it does not survive a server restart. If you restart the server mid-OTP flow, the user must re-request.
- **Game upsert logic**: `Game.query.filter_by(user_id=user.id, name=name).first()` — re-saving the same game name overwrites `game_data` and `updated_at`. No duplicate rows.
- **Multiplayer rooms are in-memory** (`_rooms` dict in `api/multiplayer.py`) — rooms don't persist across restarts. Max 2 players per room. Room ID is auto-generated 8-char uppercase string.

### Where to Take Off From

These are the natural next features in priority order:

1. **Restore Google account creation** — Google OAuth login works (`POST /google-login`) but the ability to **create a new account via Google** was accidentally removed when OTP was implemented. Users can only sign up with a password+OTP account and then link Google. The fix is in `api/user.py` — re-add the Google sign-up path so new users can register directly with their Google account.
2. **Persist OTP store to Redis** — the current in-memory dict is lost on any restart. Swap it for a Redis key with TTL so restarts don't break active login flows.
2. **Rate limiting on AI endpoints** — `/api/gemini` and `/api/ainpc/chat` are called frequently (coach calls every ~4.5 s per active game session). Add per-user rate limiting before Gemini API costs scale up.
3. **Coach dashboard API** — teachers need a view of per-participant scores and session history. The data is already in `game_scores` and `games` tables; it just needs a filtered endpoint with teacher-role auth.
4. **Migrate OTP secret storage** — `_otp_store` is not thread-safe under Gunicorn with multiple workers. Redis or a DB-backed token table is the right fix.
5. **Spanish localization for AI chat** — the UESL chat endpoint (`/api/uesl-chat`) already has a system prompt; extend it to detect language and respond in Spanish when appropriate.
6. **Tournament bracket model** — add a `Bracket` model to `model/` and REST endpoints so the frontend tournament page can create and update live brackets.
7. **Push OTP expiry to DB** — current TTL logic uses `datetime` in memory. Moving it to a `pending_otp` table makes it auditable and restart-safe.

### Running Locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python scripts/db_init.py
python main.py         # http://localhost:8424
```

See [Environment Variables](#environment-variables) for required `.env` keys.

---

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
  - [Authentication & Users](#authentication--users)
  - [Groq AI](#groq-ai)
  - [Gemini AI](#gemini-ai)
  - [Game](#game)
  - [Social & Presence](#social--presence)
  - [Analytics](#analytics)
- [Database](#database)
- [Socket.IO Multiplayer](#socketio-multiplayer)
- [Docker Deployment](#docker-deployment)
- [Production Database Management](#production-database-management)
- [Contributing](#contributing)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| REST API | Flask-RESTful (Blueprint-based) |
| Auth | Flask-Login + PyJWT (cookie-based) |
| ORM | Flask-SQLAlchemy |
| Database (dev) | SQLite3 (`instance/volumes/user_management.db`) |
| Database (prod) | MySQL on AWS RDS |
| Real-time | Flask-SocketIO (threading mode) |
| AI — LLaMA | Groq API (`llama-3.3-70b-versatile`) |
| AI — Gemini | Google Gemini 2.5 Flash |
| CORS | Flask-CORS |
| Virtual desktops | KASM API |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
MalwareMadness-backend/
├── main.py                  # Entry point — registers blueprints, startup init, routes
├── __init__.py              # Flask app factory — config, CORS, DB, Socket.IO, login
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Two services: web (8424) and socketio (8501)
├── Dockerfile               # Flask web service container
├── .env                     # Secrets (not committed — see template below)
│
├── api/                     # All REST API blueprints
│   ├── authorize.py         # @auth_required() decorator
│   ├── user.py              # /api/authenticate, /api/id, /api/user
│   ├── groq_api.py          # /api/groq, /api/uesl-chat, /api/groq/analyze
│   ├── gemini_api.py        # /api/gemini (UESLCoach taunts)
│   ├── api_ainpc.py         # /api/ainpc/chat (AI NPC dialogue)
│   ├── game_api.py          # /api/game/* (save, load, shared gallery)
│   ├── game_social_api.py   # /api/game/score, leaderboard, comments
│   ├── presence_api.py      # /api/heartbeat, /api/active-users
│   ├── friendship_api.py    # /api/friends/*
│   ├── social_api.py        # /api/messages/<uid> (DMs)
│   ├── analytics.py         # /api/analytics
│   ├── pfp.py               # /api/id/pfp (profile picture)
│   ├── otp_api.py           # /api/otp/* (one-time password)
│   └── multiplayer.py       # Socket.IO co-op room events
│
├── model/                   # SQLAlchemy database models
│   ├── user.py              # User — initUsers(), ensure_admin()
│   ├── friendship.py        # FriendRequest
│   ├── game.py              # Game
│   ├── game_score.py        # GameScore
│   └── game_comment.py      # GameComment
│
├── hacks/
│   ├── joke.py              # /api/jokes blueprint
│   └── jokes.py             # initJokes() seed data
│
├── scripts/                 # Database management scripts
│   ├── db_init.py           # Initialize DB + seed data
│   ├── db_migrate-prod2sqlite.py   # Pull production DB to local
│   └── db_restore-sqlite2prod.py   # Push local DB to production
│
└── instance/
    └── volumes/
        └── user_management.db  # SQLite dev database (auto-created)
```

---

## Local Development

### Prerequisites

- Python 3.9+
- `pip` and `venv`

### Setup

```bash
# 1. Clone and enter the project
git clone https://github.com/unified-esports-league/MalwareMadness-backend.git
cd MalwareMadness-backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file (see Environment Variables section)
cp .env.example .env
# edit .env with your actual keys

# 5. Initialize the database
python scripts/db_init.py

# 6. Run the server
python main.py
```

Server starts at **http://localhost:8424**.

### VSCode Setup

1. Open the project in VSCode: `code .`
2. **Cmd/Ctrl+Shift+P** → "Python: Select Interpreter" → choose `./venv/bin/python`
3. Install the **SQLite3 Editor** extension to browse `instance/volumes/user_management.db`
4. Run/debug `main.py` with the Play button

---

## Environment Variables

Create a `.env` file in the project root. These are the only variables you need to get the platform running:

```env
# --- Admin account (seeded on first db_init) ---
ADMIN_USER='Your Name'
ADMIN_UID='youruid'
ADMIN_PASSWORD='YourPassword!'

# --- Groq AI (general chat + UESL chatbot) ---
# Get a free key at https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GROQ_SERVER=https://api.groq.com/openai/v1/chat/completions

# --- Google Gemini AI (UESLCoach taunts + AI NPCs) ---
# Get a free key at https://aistudio.google.com/api-keys
GEMINI_API_KEY=xxxxx
GEMINI_SERVER=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent

# --- OTP email (see OTP Setup section below) ---
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password

# --- Production database (leave false for local dev) ---
IS_PRODUCTION=false
```

---

## OTP Setup

OTP login sends a 6-digit code to the user's email via Gmail SMTP. To enable it you need a **dedicated Gmail account** — do not use a personal account.

### Steps

1. **Create a new Gmail account** — e.g. `uesl.noreply@gmail.com`. This is the address OTP emails will come from.

2. **Enable 2-Step Verification** on that account:  
   Google Account → Security → 2-Step Verification → Turn on

3. **Generate an App Password**:  
   Google Account → Security → 2-Step Verification → App passwords  
   Name it anything (e.g. "UESL OTP"), copy the 16-character password.

4. **Set your `.env`**:
   ```env
   SMTP_USER=uesl.noreply@gmail.com
   SMTP_PASSWORD=abcd efgh ijkl mnop   # the 16-char app password (spaces ok)
   ```

5. **Test it**: start the server, register a user with `_auth_type='otp'`, and hit `POST /api/otp/send`. The code will arrive in their inbox — or print to the console if `SMTP_USER`/`SMTP_PASSWORD` are missing (dev fallback).

> **Note**: the OTP store is in-memory (`_otp_store` dict in `api/otp_api.py`). Codes expire after 10 minutes and are wiped on server restart. If you need persistence across restarts, replace it with a Redis key or a DB-backed table.

---

## API Endpoints

### Authentication & Users

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/authenticate` | No | Login — returns JWT cookie |
| GET | `/api/id` | Yes | Get current logged-in user info |
| POST | `/api/user` | No | Create new user account (signup) |
| PUT | `/api/user` | Yes | Update current user |
| DELETE | `/api/user` | Yes | Delete current user account |
| GET | `/api/user/preferences` | Yes | Get user theme/accessibility preferences |
| PUT | `/api/user/preferences` | Yes | Save user preferences |
| POST | `/api/pfp` | Yes | Upload profile picture |
| GET | `/uploads/<filename>` | No | Serve uploaded files (PFPs) |
| POST | `/api/otp/send` | No | Send one-time password via email |
| POST | `/api/otp/verify` | No | Verify OTP |
| GET | `/login` | No | Login page (Jinja2) |
| POST | `/google-login` | No | Google OAuth login |
| GET | `/logout` | No | Log out |

### Groq AI

All Groq endpoints use model `llama-3.3-70b-versatile` by default.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/groq` | No | Basic completion — `{"prompt": "..."}` |
| POST | `/api/groq/chat` | No | Chat with message history — `{"messages": [...]}` |
| POST | `/api/groq/analyze` | No | Text analysis — `{"text": "...", "task": "summarize\|sentiment\|keywords\|custom"}` |
| GET | `/api/groq/models` | No | List available Groq models |
| GET | `/api/groq/health` | No | Health check for Groq API |
| POST | `/api/uesl-chat` | No | UESL chatbot — context-aware, knows UESL mission and locations |

**Analyze tasks** (temperature 0.3, max 500 tokens):
- `summarize`: "Summarize this text concisely in 2–3 sentences."
- `sentiment`: Classifies positive/negative/neutral with confidence
- `keywords`: Extracts key topics
- `custom`: Pass your own prompt via `"prompt"` field

**UESL Chat** (temperature 0.7, max 400 tokens):
- Knows UESL mission, locations, contact (Spanish support: Wendy Munoz), games, and values
- Maintains sliding window of last 10 user messages
- Used by the frontend accessibility toolkit's built-in chatbot

### Gemini AI

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/gemini` | No | Chat with Google Gemini 2.5 Flash |

### Game

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/games` | No | List all games |
| POST | `/api/games` | Yes | Create a new game entry |
| PUT | `/api/games/<id>` | Yes | Update a game |
| DELETE | `/api/games/<id>` | Yes (Admin) | Delete a game |
| GET | `/api/scores` | No | Get leaderboard scores |
| POST | `/api/scores` | Yes | Submit a game score |
| GET | `/api/game-comments` | No | Get comments for a game |
| POST | `/api/game-comments` | Yes | Post a game comment |

### Social & Presence

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/heartbeat` | Yes | Update online presence (call every ~120s) |
| GET | `/api/active-users` | Yes | Get list of users active in last 5 minutes |
| POST | `/api/friends/request` | Yes | Send a friend request |
| POST | `/api/friends/respond` | Yes | Accept or decline a friend request |
| GET | `/api/friends` | Yes | Get friends list with online status |
| GET | `/api/messages/<uid>` | Yes | Get DMs with a user |
| POST | `/api/messages/<uid>` | Yes | Send a DM (text, emoji, or base64 image) |

### Analytics

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/analytics` | Yes (Admin) | Site analytics (user registrations, activity) |

---

## Database

### Models

| Model | Table | Key Fields |
|---|---|---|
| `User` | `users` | `_uid`, `_name`, `_email`, `_password`, `_role`, `_auth_type`, `_pfp` |
| `FriendRequest` | `friend_requests` | `sender_id`, `receiver_id`, `status` |
| `Game` | `games` | `name`, `game_data`, `user_id`, `updated_at` |
| `GameScore` | `game_scores` | `game_id`, `user_id`, `score`, `levels_completed`, `played_at` |
| `GameComment` | `game_comments` | `game_id`, `user_id`, `body`, `posted_at` |

### Dev vs. Production

| Environment | Database | Config |
|---|---|---|
| Local (`IS_PRODUCTION=false`) | SQLite — `instance/volumes/user_management.db` | Auto-created on first run |
| Production (`IS_PRODUCTION=true`) | MySQL on AWS RDS | Requires `DB_USERNAME`, `DB_PASSWORD` |

### Startup behavior

On first run, `main.py` automatically:
1. Runs `db.create_all()` to create all tables
2. Calls `initUsers()` (only if user table is empty — avoids duplicates on restart)
3. Calls `ensure_admin()` to guarantee an admin superuser exists

---

## Socket.IO Multiplayer

Real-time multiplayer is handled by a **separate Socket.IO service** in `api/multiplayer.py`.

- Runs on port **8501** (separate Docker container)
- Registered event handlers on the `socketio` instance from `__init__.py`
- Frontend connects via `io('https://uesl.opencodingsociety.com:8501')` or `io('http://localhost:8501')` locally

---

## Docker Deployment

Two services are defined in `docker-compose.yml`:

```yaml
services:
  web:
    image: flask_open
    ports:
      - "8424:8424"
    volumes:
      - ./instance:/app/instance   # persists SQLite DB
  socketio:
    image: socket_open
    ports:
      - "8501:8501"
```

### Deploy

```bash
# Build and start both services
docker-compose up --build -d

# View logs
docker-compose logs -f web
docker-compose logs -f socketio

# Stop
docker-compose down
```

### Production setup (Ubuntu + Nginx)

Nginx reverse proxies:
- `https://uesl.opencodingsociety.com` → Flask on port 8424
- `wss://uesl.opencodingsociety.com:8501` → Socket.IO on port 8501

---

## Production Database Management

Use these scripts when updating the production database schema:

```bash
# 1. Initialize local DB with clean seed data
python scripts/db_init.py

# 2. Pull production data to local (for testing with real data)
python scripts/db_migrate-prod2sqlite.py

# 3. Test your changes locally

# 4. On the production server (in cockpit):
#    a. Backup: cp sqlite.db backups/sqlite_$(date +%Y-%m-%d).db
#    b. Pull code: git pull
#    c. Update schema: python scripts/db_init.py

# 5. Push local data to production (requires production admin password in .env)
python scripts/db_restore-sqlite2prod.py
```

---

## CORS

The following origins are allowed:

| Origin | Use |
|---|---|
| `http://localhost:4700` | Jekyll dev server |
| `http://localhost:4500` | Alternate Jekyll port |
| `http://localhost:4599` | Alternate |
| `http://localhost:4600` | Alternate |
| `http://localhost:4000` | Alternate |
| `https://unified-esports-league.github.io` | GitHub Pages |
| `https://uesl.io` | Production domain |

---

## Contributing

This project is **retired** by the original team. If you want to build on it, use it as a template rather than forking:

1. Click **Use this template** on GitHub to create your own repo from this codebase
2. Copy `.env.example` to `.env` and fill in your own API keys (Groq, Gemini, SMTP, etc.)
3. Run `python scripts/db_init.py` to initialize a fresh database
4. The auth system, game API, social features, and Socket.IO multiplayer are all yours to extend

If you're continuing UESL specifically, see the [Project Status & Roadmap](#project-status--roadmap) section for what's working and where to start.

### Adding a new API endpoint

1. Create `api/your_feature_api.py` with a Flask Blueprint
2. Import and register in `main.py`:
   ```python
   from api.your_feature_api import your_feature_api
   app.register_blueprint(your_feature_api)
   ```
3. Add the `@auth_required()` decorator from `api/authorize.py` if authentication is needed
4. Add a SQLAlchemy model to `model/` if the feature needs DB persistence

---

## Team

Built by the **UESL / MalwareMadness** team for AP CSP 2025–2026.

- Groq AI integration (`groq_api.py`): UESL chatbot, summarize, analyze — **Sathwik Kintada** (Wick2009)
- Presence / active users (`presence_api.py`) — Rudra
- Friendship system (`friendship_api.py`) — teammate contribution
- Login, OTP, user auth — teammate contribution
- Game API, scores, comments — teammate contribution
- Socket.IO multiplayer — teammate contribution
- Microblog, social posts — teammate contribution
