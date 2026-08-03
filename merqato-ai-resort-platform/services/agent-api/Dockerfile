FROM python:3.11-slim-bookworm

WORKDIR /app

# Install uv package manager (faster, deterministic installs).
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Copy lockfile and package manifest first for layer caching.
COPY pyproject.toml uv.lock ./

# Install production dependencies only.
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application source.
COPY app/ ./app/

# Expose FastAPI port.
EXPOSE 8000

# Run the concierge API.  Environment variables are injected at deploy time
# via the platform secret manager (OPENROUTER_API_KEY, QDRANT_URL, etc.).
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
