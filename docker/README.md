# Docker Setup

This document describes how to run DataGenFlow using Docker.

## Quick Start

1. **Build and start the application:**

   ```bash
   docker-compose up -d
   ```

2. **Access the application:**
   - Frontend: <http://localhost:8000>
   - API: <http://localhost:8000/api>

3. **Stop the application:**

   ```bash
   docker-compose down
   ```

## Custom Blocks

Custom blocks can be added to `lib/blocks/custom/` on your host system. They will be automatically available after restarting the backend container:

```bash
docker-compose restart backend
```

The `lib/blocks/custom/` directory is mounted as a volume, so you can add new block files directly from your host system without rebuilding the image.

## Environment Variables

You can configure the application using environment variables. Create a `.env` file in the project root:

```env
LLM_ENDPOINT=http://localhost:11434/api/generate
LLM_API_KEY=
LLM_MODEL=llama3
DEBUG=false
```

These variables are automatically passed to the container via `docker-compose.yml`.

## Data Persistence

The `data/` directory is mounted as a volume, so your database and other data will persist between container restarts.

## Building Images

To rebuild the images:

```bash
docker-compose build
```

Or rebuild without cache:

```bash
docker-compose build --no-cache
```

## Development

For development, you may want to mount additional directories or use volume mounts for live code reloading. Modify `docker-compose.yml` as needed.

## Architecture

- **Backend**: Python 3.11 with uv, serves both API and frontend
- **Frontend**: Built with yarn/vite, served as static files by the backend
- **Port**: 8000 (both API and frontend)

The backend Dockerfile:

- Uses multi-stage builds for optimization
- Compiles Python bytecode for faster startup
- Builds the frontend and includes it in the final image
- Serves the frontend at the root path via FastAPI
