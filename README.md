# Eagle Eye Backend
### Smart Class Attendance & Activity Intelligence - FastAPI Real-Time AI Core

The high-performance, asynchronous REST & WebSocket API backend powering the Eagle Eye smart classroom attendance verification, biometric surveillance, and spatial tracking system.

Built with **Python 3.12**, **FastAPI**, **WebSockets**, **Uvicorn**, **OpenCV**, and **SQLite / PostgreSQL Dual-Engine**.

---

## 🚀 Features

- **🎓 Attendance Intelligence**:
  - `GET /api/attendance` — Filtered classroom attendance roster.
  - `POST /api/attendance/mark` — Biometric verification and manual override logging.
  - `POST /api/attendance/scan` — Autonomous multi-subject facial scan.
  - `GET /api/attendance/summary` — Real-time attendance rate and proxy anomaly statistics.
  - `GET /api/attendance/export` — Audit-ready CSV file download.
- **📡 Real-Time WebSocket Gateway (`/ws`)**:
  - Instant broadcasts for `ATTENDANCE_UPDATED`, `ATTENDANCE_SCAN_COMPLETED`, `NEW_PERSON_ENROLLED`, and `NEW_ALERT`.
- **📹 Universal Camera Ingestion**:
  - RTSP, ONVIF, and USB webcam ingestion with live MJPEG streaming (`/api/cameras/{id}/live-feed`).
- **👤 Biometric Face Recognition**:
  - 512-D normalized facial embedding extraction with cosine similarity matching (>85% verification threshold).
- **🛡️ Threat Mitigation & Geofencing**:
  - Detection of proxy attendance, turnstile tailgating, restricted lab intrusions, and corridor loitering.
- **💾 Dual-Engine Storage**:
  - Runs out-of-the-box on embedded SQLite or scales to PostgreSQL / Supabase via `DATABASE_URL`.

---

## 🛠️ Local Development

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- pip

### Setup & Run
```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # On Linux/macOS
# or: .\venv\Scripts\Activate.ps1   # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server with auto-reload
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger documentation.

---

## 🌐 Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `PORT` | HTTP port to listen on | `8000` |
| `ENVIRONMENT` | Environment name (`development` or `production`) | `production` |
| `DATABASE_URL` | SQLite path or PostgreSQL connection string | `sqlite:///data/eagle_eye.db` |
| `CORS_ORIGINS` | Permitted frontend origins (`*` or comma-separated URLs) | `*` |
| `JWT_SECRET_KEY` | Secret key for signing authentication tokens | *(Auto-generated)* |
| `STORAGE_BACKEND` | Storage backend for face crops (`local` or `s3`) | `local` |

---

## 📦 Production Deployment

### Option 1: Deploy to Render (Recommended)
1. Push this repository to GitHub.
2. In [Render](https://render.com), click **New +** → **Blueprint** and connect your repository.
3. Render automatically picks up `render.yaml`.
4. Alternatively, create a **Web Service**:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables (`CORS_ORIGINS`, `ENVIRONMENT=production`).
5. Click **Deploy**.

---

### Option 2: Deploy to Railway
1. In [Railway](https://railway.app), click **New Project** → **Deploy from GitHub repo**.
2. Railway detects the `Procfile` or `Dockerfile` automatically.
3. Add a persistent volume mounted at `/app/data` to persist media crops and SQLite data (or add a Railway PostgreSQL service and attach `DATABASE_URL`).
4. Set `PORT` environment variable (Railway injects `$PORT` automatically).

---

### Option 3: Deploy to Fly.io
```bash
# Authenticate
fly auth login

# Launch from included fly.toml
fly launch

# Deploy
fly deploy
```

---

### Option 4: Deploy with Docker / Docker Compose
```bash
# Option A: Build and run single container
docker build -t eagle-eye-backend .
docker run -d -p 8000:8000 -v backend-data:/app/data --name eagle-eye-backend eagle-eye-backend

# Option B: Docker Compose
docker-compose up -d
```

---

## 🧪 Health & API Verification

```bash
# Check service health
curl http://localhost:8000/api/health

# Check live attendance metrics
curl http://localhost:8000/api/attendance/summary

# Export CSV report
curl -OJ http://localhost:8000/api/attendance/export
```
