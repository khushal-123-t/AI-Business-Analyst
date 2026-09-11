# AI Business Analyst

An enterprise-grade, AI-powered Business Intelligence & SQL Analytics SaaS platform. It transforms commercial datasets (CSV/Excel) into interactive visualizations, KPIs, automated SQLite queries, and actionable executive insights using Google Gemini GenAI.

---

## Features

- **Public SaaS Landing Page**: High-converting marketing homepage showcasing core capabilities, interactive sample Q&A previews, and workflow breakdowns.
- **Natural Language to SQL**: Powered exclusively by Google Gemini GenAI (`gemini-3.6-flash`). Automatically understands uploaded dataset schemas and generates safe, read-only SQLite queries.
- **Strict Profit & Financial Integrity**: Guarantees zero assumed or fabricated profit margins (no default 18% assumption). Only computes profit when actual profit/margin columns exist or the user explicitly specifies one.
- **Multi-Tenant Data Isolation**: Separate client accounts with individual table namespaces, ensuring clients query only authorized datasets.
- **Interactive Dashboards**: Real-time KPI metric cards, temporal sales trend lines, category distribution charts, and regional breakdowns.
- **Dataset Ingestion**: Support for CSV and Excel (.xlsx) file uploads with instant parsing, sanitization, and automatic schema mapping.
- **Authentication & User Management**: Secure JWT authentication with native `bcrypt` password hashing, public registration (`/signup`), and role-based portal routing (`/admin/*` and `/client/*`).

---

## Application Architecture & Flow

```
                      AI BUSINESS ANALYST
                               │
                               ↓
                        LANDING PAGE (/)
                               │
               ┌───────────────┴───────────────┐
               ↓                               ↓
       GET STARTED / SIGN UP                 LOGIN
           (/signup)                       (/login)
               ↓                               ↓
          SIGN UP PAGE                       LOGIN
               ↓                               ↓
          LOGIN PAGE                     AUTHENTICATED
               ↓                           DASHBOARD
          AUTHENTICATED              (/client/dashboard or
            DASHBOARD                  /admin/dashboard)
```

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Uvicorn, Pandas, OpenPyXL, PyJWT, Bcrypt
- **AI / LLM**: Google Gemini SDK (`google-genai`), Model: `gemini-3.6-flash` (Sole AI Provider, zero Ollama dependency)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons, Recharts
- **Database**: SQLite (`business.db`) with client-isolated table partitioning

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/khushal-123-t/AI-Business-Analyst.git
cd AI-Business-Analyst
```

### 2. Backend Setup

```bash
# Create and activate Python 3.12 virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
DATABASE_URL=sqlite:///database/business.db
PORT=8000
HOST=127.0.0.1
JWT_SECRET=supersecretjwtkey_insightgen_2026
```

Start the FastAPI server:
```bash
uvicorn backend.main:app --reload --port 8000
```
Backend will be available at `http://127.0.0.1:8000` (Docs: `http://127.0.0.1:8000/docs`).

### 3. Frontend Setup

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend will be available at `http://localhost:5173`.

---

## Default Demo Credentials

For quick evaluation, pre-seeded accounts are available:

- **Client User**:
  - Email: `client1@example.com`
  - Password: `client123`
- **Admin User**:
  - Email: `admin@example.com`
  - Password: `admin123`

---

## Deployment (Render)

The backend is pre-configured for deployment as a Web Service on Render:

- **Build Command**: `pip install -r requirements.txt` (or `pip install -r backend/requirements.txt`)
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Python Version**: Pinned to `3.12.10` via `.python-version`
- **Environment Variables to Set in Render**:
  - `LLM_PROVIDER`: `gemini`
  - `GEMINI_API_KEY`: `<your_gemini_api_key>`
  - `GEMINI_MODEL`: `gemini-3.6-flash`
  - `JWT_SECRET`: `<your_jwt_secret>`
  - `DATABASE_URL`: `sqlite:///database/business.db`

---

## License

MIT License.
