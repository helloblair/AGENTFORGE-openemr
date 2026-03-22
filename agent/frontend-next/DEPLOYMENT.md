# Deployment Guide — OpenEMR Agent Frontend

## Local Development

```bash
cd agent/frontend-next
cp .env.example .env.local   # then edit as needed
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_AGENT_API_URL` | URL of the agent FastAPI backend | `http://localhost:8080` |

## Deploy to Vultr VPS (Production)

The frontend runs as part of the full-stack Docker Compose setup. From the repo root:

```bash
# First time:
cp .env.production.example .env.production
# Edit .env.production — set DOMAIN, API keys, passwords

# Build and start all services:
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

The `NEXT_PUBLIC_AGENT_API_URL` is passed as a Docker build arg from `docker-compose.prod.yml` and baked into the Next.js static output at build time.

Nginx routes `https://YOUR_IP/` to the frontend and `https://YOUR_IP/api/` to the agent.

## Deploy with Docker (Standalone)

Build and run the container independently:

```bash
cd agent/frontend-next
docker build -t agent-frontend \
  --build-arg NEXT_PUBLIC_AGENT_API_URL=https://your-agent-api.example.com .
docker run -p 3000:3000 agent-frontend
```

The Dockerfile uses a multi-stage build with `output: "standalone"` for a minimal production image.

## Production Build (without Docker)

```bash
npm run build
npm start
```

The app listens on port 3000 by default.
