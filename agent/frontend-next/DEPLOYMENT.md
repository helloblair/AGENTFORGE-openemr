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
| `NEXT_PUBLIC_AGENT_API_URL` | URL of the agent FastAPI backend | `http://localhost:8400` |

## Deploy to Vercel

1. Connect your GitHub repository to [Vercel](https://vercel.com).
2. Set the **Root Directory** to `agent/frontend-next`.
3. Add the environment variable `NEXT_PUBLIC_AGENT_API_URL` pointing to your production agent API.
4. Deploy. Vercel auto-detects the Next.js framework via `vercel.json`.

## Deploy with Docker (Fly.io / Railway)

Build and run the container:

```bash
cd agent/frontend-next
docker build -t agent-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_AGENT_API_URL=https://your-agent-api.example.com \
  agent-frontend
```

The Dockerfile uses a multi-stage build with `output: "standalone"` for a minimal production image.

## Production Build (without Docker)

```bash
npm run build
npm start
```

The app listens on port 3000 by default.
