# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first (cached layer)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy frontend (served as static files by FastAPI)
COPY frontend/ ./frontend/

# ── Runtime ────────────────────────────────────────────────────────────────────
WORKDIR /app/backend

ENV DATABASE_URL=sqlite:///./data/sales_crm.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
