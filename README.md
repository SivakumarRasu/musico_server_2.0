# 🎵 Musico Server 2.0

A production-grade **FastAPI** backend powering the **Musico** music streaming application. It provides REST APIs for authentication, online music streaming (via JioSaavn), local song management, playlists, AI-powered recommendations, real-time listening rooms (WebSocket), payments (Razorpay), and an admin management portal.

---

## 📐 Architecture Overview

```
musico_server/
├── main.py                  # App entry point, CORS, route registration
├── database.py              # SQLAlchemy engine & session
├── endpoints.py             # JioSaavn API base URLs
├── helper.py                # Shared utilities (song formatter, color extractor, DES decrypt)
├── prints.py                # Debug utilities
│
├── routes/                  # API route handlers
│   ├── auth.py              # User signup / login / JWT / password reset
│   ├── online_songs.py      # JioSaavn search, albums, playlists, AI recommendations
│   ├── song_list.py         # Local song upload & listing (Cloudinary)
│   ├── playlist.py          # Playlist CRUD (Cloudinary thumbnails)
│   ├── payments.py          # Razorpay order creation
│   ├── premium.py           # Subscription webhook handler
│   ├── websocket.py         # Real-time listening room (WebSocket)
│   ├── webhook.py           # Razorpay raw webhook listener
│   └── manage.py            # Admin management portal
│
├── models/                  # SQLAlchemy ORM models
│   ├── user.py
│   ├── songs.py
│   ├── playlist.py
│   ├── payment.py
│   ├── app_version.py
│   └── sync_event.py
│
├── services/                # External service integrations
│   ├── gemini_service.py    # Google Gemini + Groq AI recommendations
│   ├── mail_services.py     # SMTP email (OTP, welcome, subscription)
│   ├── payment_services.py  # Razorpay client
│   └── s3_service.py        # AWS S3 presigned URLs & direct upload
│
├── middleware/
│   └── auth_middleware.py   # JWT Bearer token validation
│
├── security/
│   └── document_security.py # HTTP Basic Auth for /docs protection
│
├── websocket/
│   └── room_manager.py      # WebSocket room state manager
│
├── pydantic_shemas/         # Pydantic request/response schemas
├── .env                     # 🔐 Secret keys (NOT committed to Git)
├── .env.example             # ✅ Safe template for onboarding
└── requirements.txt         # Python dependencies
```

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy ORM |
| Auth | JWT (PyJWT) + bcrypt |
| Cloud Storage | Cloudinary (profiles, songs) / AWS S3 (APK releases) |
| Email | Gmail SMTP via fastapi-mail |
| AI / LLM | Google Gemini API + Groq API |
| Payments | Razorpay |
| Music Source | JioSaavn Unofficial API |
| Real-time | WebSocket (FastAPI native) |
| Server | Uvicorn / Gunicorn |

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10+
- PostgreSQL (running locally or remote)
- A virtual environment tool (`venv` or `conda`)

### 1. Clone the repository

```bash
git clone https://github.com/SivakumarRasu/musico_server_2.0.git
cd musico_server_2.0
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example template and fill in your actual credentials:

```bash
cp .env.example .env
```

Then edit `.env` with your values:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/musicapp
JWT_SECRET=your_strong_jwt_secret

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-south-2
AWS_S3_BUCKET=your_bucket_name

SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

DOCS_USERNAME=admin@musico
DOCS_PASSWORD=your_docs_password

CORS_ORIGINS=http://localhost:5173,https://your-production-domain.com
APP_FRONTEND_URL=http://localhost:5173
```

### 5. Set up the PostgreSQL database

Create a database named `musicapp` (or whatever name you put in `DATABASE_URL`):

```sql
CREATE DATABASE musicapp;
```

Tables are created automatically on server startup via SQLAlchemy `create_all`.

---

## ▶️ Running the Server

### Development (hot reload)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Gunicorn + Uvicorn workers)

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

The API will be available at: `http://localhost:8000`

---

## 📚 API Documentation

Interactive docs are protected with HTTP Basic Auth (configured via `DOCS_USERNAME` / `DOCS_PASSWORD` in `.env`).

| URL | Description |
|---|---|
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc UI |

---

## 🔌 API Endpoints Reference

### 🔐 Authentication — `/auth`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | ❌ | Register a new user with name, email, password & profile photo |
| `POST` | `/auth/login` | ❌ | Login with email & password, returns JWT token |
| `GET` | `/auth/` | ✅ JWT | Get the currently authenticated user |
| `POST` | `/auth/secure/login` | ❌ | Single-device login (binds session to device ID) |
| `GET` | `/auth/secure` | ✅ JWT | Get current user with device session validation |
| `GET` | `/auth/send_forgot_password_otp` | ❌ | Send a 6-digit OTP to user's email for password reset |
| `PATCH` | `/auth/forget_password` | ❌ | Reset password using verified OTP |
| `GET` | `/auth/user-exists-with-email` | ❌ | Check if a user exists with a given email |

---

### 🎵 Online Songs (JioSaavn) — `/api`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/search/songs/` | ✅ JWT | Search for songs by query text |
| `POST` | `/api/search/autocomplete/` | ❌ | Autocomplete search (returns albums + playlists) |
| `POST` | `/api/searchv2` | ❌ | Unified search returning songs, albums, and playlists |
| `GET` | `/api/album/` | ✅ JWT | Get full album details by album ID |
| `GET` | `/api/getplaylist/` | ✅ JWT | Get full JioSaavn playlist details by playlist ID |
| `GET` | `/api/color` | ❌ | Extract dominant hex color from an image URL |
| `GET` | `/api/client-version` | ❌ | Get the latest active Musico app version info |
| `POST` | `/api/recommend` | ❌ | AI-powered personalized song recommendations (Gemini + Groq) |

---

### 💿 Local Songs — `/local/songs`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/local/songs/upload` | ✅ JWT | Upload a song and thumbnail to Cloudinary |
| `GET` | `/local/songs/get` | ✅ JWT | Get all locally uploaded songs |

---

### 📂 Playlists — `/playlist`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/playlist/create` | ✅ JWT | Create a new playlist with thumbnail |
| `GET` | `/playlist/get` | ✅ JWT | Get all playlists for the authenticated user |
| `POST` | `/playlist/add_song` | ✅ JWT | Add an existing song to a playlist |
| `POST` | `/playlist/add_new_song` | ✅ JWT | Add a new song entry directly to a playlist |
| `DELETE` | `/playlist/delete_playlist` | ✅ JWT | Delete a playlist |
| `DELETE` | `/playlist/delete_song_from_playlist` | ✅ JWT | Remove a song from a playlist |

---

### 💳 Payments — `/payments`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/payments/create-order` | ❌ | Create a Razorpay payment order, returns order ID + public key |
| `GET` | `/payments/get-all-payments` | ❌ | Get all recorded payment transactions |
| `GET` | `/payments/get-user-payments` | ✅ JWT | Get all payments for a specific user email |

---

### 👑 Subscription — `/subscribe`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/subscribe/webhook` | ❌ | Razorpay webhook handler — verifies signature, records payment, creates user account, and sends welcome email |

---

### 🔴 Real-Time Rooms — `/sync`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `WS` | `/sync/ws/{room_id}` | ❌ | WebSocket connection for a listening room (sync playback state) |
| `POST` | `/sync/create-room` | ❌ | Create a new listening room, returns a 6-char room code |
| `GET` | `/sync/room/{room_id}` | ❌ | Check if a room ID is currently active |

---

### 🛠️ Management Portal — `/manage`

> All endpoints require Admin credentials (`DOCS_USERNAME` / `DOCS_PASSWORD` via HTTP Basic Auth or `X-Admin-Key` header).

#### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/manage/stats` | Overview: total users, playlists, songs, payments, and revenue |

#### User Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/manage/users` | List all users (searchable, paginated) |
| `GET` | `/manage/users/{user_id}` | Get user detail with playlists and payments |
| `PATCH` | `/manage/users/{user_id}/password` | Update a user's password |
| `PUT` | `/manage/users/{user_id}/profile-pic` | Update a user's profile picture |
| `DELETE` | `/manage/users/{user_id}` | Safely delete a user and all their playlists |

#### Playlist Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/manage/playlists` | List all playlists across all users |
| `GET` | `/manage/playlists/{playlist_id}` | Get single playlist with full song list |
| `GET` | `/manage/users/{user_id}/playlists` | List playlists for a specific user |
| `DELETE` | `/manage/playlists/{playlist_id}` | Delete any playlist as admin |

#### Payment Auditing
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/manage/payments` | List all payments (filterable by status, searchable, paginated) |
| `GET` | `/manage/payments/user/{email}` | Get all payments for a specific email |

#### App Version & S3 Releases
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/manage/version` | Get the current active app version |
| `GET` | `/manage/version/history` | List all release version history |
| `POST` | `/manage/version` | Publish a new app version |
| `POST` | `/manage/version/{version_id}/activate` | Rollback / activate a specific version |
| `GET` | `/manage/version/s3-status` | Check AWS S3 credentials configuration status |
| `POST` | `/manage/version/presigned-url` | Generate a pre-signed S3 URL for APK upload |
| `POST` | `/manage/version/upload-fallback` | Server-side fallback upload to S3 |

---

## 🔐 Authentication

All protected endpoints require a `auth-token` header:

```
auth-token: <jwt_token>
```

The JWT token is returned on `/auth/login` or `/auth/secure/login`. It encodes the user's `id` and optionally `device_id`.

---

## 🤖 AI Recommendations

The `/api/recommend` endpoint uses a multi-model fallback strategy:

1. **Google Gemini** (`gemini-3.5-flash-lite` → `gemini-3.6-flash`) — Primary
2. **Groq** (`openai/gpt-oss-120b` → `openai/gpt-oss-20b`) — Fallback

The pipeline:
- Analyses user listening history
- Generates personalized song titles/artists
- Searches JioSaavn for real song data matching the AI suggestions
- Deduplicates results and returns full song objects with stream URLs

---

## 📬 Email Notifications

Triggered automatically on:
- **Password reset** — OTP email
- **New user registration via payment** — Welcome email with premium feature list
- **Subscription activated** — Plan & expiry confirmation

Emails are sent in **background tasks** to keep API responses fast.

---

## 🔒 Security Notes

- `.env` is excluded from Git via `.gitignore` — **never commit it**
- Use `.env.example` as the safe template to share with collaborators
- API docs (`/docs`, `/redoc`) are protected with HTTP Basic Auth
- JWT tokens are verified on every protected route
- Razorpay webhooks are verified using HMAC-SHA256 signature comparison

---

## 📦 Key Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` / `gunicorn` | ASGI server |
| `sqlalchemy` + `psycopg2-binary` | ORM + PostgreSQL driver |
| `pyjwt` | JWT encoding/decoding |
| `bcrypt` | Password hashing |
| `cloudinary` | Cloud image/audio storage |
| `boto3` | AWS S3 integration |
| `fastapi-mail` | Email sending |
| `google-genai` | Google Gemini AI |
| `groq` | Groq AI fallback |
| `razorpay` | Payment gateway |
| `httpx` | Async HTTP client |
| `python-dotenv` | `.env` file loading |
| `pyDes` | DES decryption for JioSaavn URLs |
| `pillow` + `numpy` | Dominant color extraction from images |

---

## 👤 Author

**Sivakumar Rasu**
- GitHub: [@SivakumarRasu](https://github.com/SivakumarRasu)
