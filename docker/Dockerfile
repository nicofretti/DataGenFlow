# Backend Dockerfile using uv
FROM python:3.10-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Compile Python bytecode for faster startup
# Compile all Python files recursively in lib/ and root
RUN python -m compileall -b -q -r lib/ && \
    python -m compileall -b -q app.py config.py models.py mock_llm.py debug_pipeline.py 2>/dev/null || true

# Frontend build stage
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy frontend package files
COPY frontend/package.json frontend/yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build the frontend
RUN yarn build

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install uv in production image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code and compiled bytecode
# Copy lib directory (includes templates, blocks, etc. and their .pyc files)
COPY --from=builder /app/lib /app/lib
# Copy main application files (including .pyc files if they exist)
COPY --from=builder /app/app.py* /app/
COPY --from=builder /app/config.py* /app/
COPY --from=builder /app/models.py* /app/
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/build /app/frontend/build

# Create data directory and ensure custom blocks directory exists
RUN mkdir -p /app/data /app/lib/blocks/custom

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

