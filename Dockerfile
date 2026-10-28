# ---- 1. build the React app
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---- 2. python runtime serving API + built SPA
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY scripts/ scripts/
COPY data/ data/
COPY --from=web /web/dist backend/static

# Fetch the January-2026 snapshot at build time unless data/ already contains it
# (build with --build-arg SKIP_FETCH=1 to use a committed snapshot).
ARG SKIP_FETCH=0
RUN if [ "$SKIP_FETCH" != "1" ] && [ ! -f data/wind_forecast.csv ]; then python scripts/fetch_data.py; fi

WORKDIR /app/backend
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
