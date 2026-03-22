# Veris — Clinical Intelligence

AI-powered clinical decision support for OpenEMR.

## Tech Stack

- **Framework:** Next.js 16, React 19, TypeScript
- **Styling:** Tailwind CSS v4
- **Rendering:** React Markdown + remark-gfm
- **Notifications:** Sonner
- **Deployment:** Docker Compose (Vultr VPS)

## Getting Started

### Prerequisites

- Node.js 20+

### Setup

```bash
npm install
cp .env.example .env.local   # fill in NEXT_PUBLIC_AGENT_API_URL
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Architecture

```
┌──────────────────── Vultr VPS ────────────────────────┐
│                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐ │
│  │ Next.js  │    │ FastAPI  │    │ OpenEMR + MariaDB│ │
│  │ Frontend │───▶│ Agent    │───▶│ Backend          │ │
│  │ :3000    │API │ :8080    │FHIR│ :80              │ │
│  └──────────┘    └──────────┘    └──────────────────┘ │
│                                                       │
│  Nginx reverse proxy (:443 / :8443)                   │
└───────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_AGENT_API_URL` | Yes | FastAPI backend URL (e.g. `https://YOUR_VPS_IP/api`) |

## Deployment

All services run on a single Vultr VPS via Docker Compose:

```bash
# From repo root:
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Folder Structure

```
agent/frontend-next/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout (fonts, metadata, providers)
│   ├── page.tsx            # Main chat page
│   ├── globals.css         # Global styles and Tailwind imports
│   └── favicon.ico         # App icon
├── components/             # React components
│   ├── ChatInput.tsx       # Message input with keyboard shortcuts
│   ├── ChatWindow.tsx      # Main chat container and message list
│   ├── ClinicalDisclaimer.tsx  # Medical disclaimer banner
│   ├── ConfidenceBar.tsx   # AI confidence score indicator
│   ├── CopyButton.tsx      # Copy-to-clipboard button
│   ├── ErrorBanner.tsx     # Error state display
│   ├── EscalationWarning.tsx   # Clinical escalation alert
│   ├── FeedbackButtons.tsx # Thumbs up/down feedback
│   ├── Header.tsx          # App header with branding
│   ├── LoadingIndicator.tsx # Typing/loading animation
│   ├── MessageBubble.tsx   # Individual message renderer
│   ├── Sidebar.tsx         # Conversation sidebar
│   ├── ThemeProvider.tsx   # Dark/light theme context
│   ├── ThemeToggle.tsx     # Theme switcher button
│   └── ToolCallsPanel.tsx  # Expandable tool call details
├── lib/                    # Shared utilities
│   ├── api.ts              # API client (sendMessage, sendFeedback, checkHealth)
│   ├── types.ts            # TypeScript type definitions
│   └── hooks/
│       └── useKeyboardShortcuts.ts  # Keyboard shortcut hook
├── public/                 # Static assets (favicon, icons)
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── next.config.ts          # Next.js configuration
├── postcss.config.mjs      # PostCSS / Tailwind setup
├── vercel.json             # Vercel deployment settings
├── Dockerfile              # Multi-stage Docker build
└── DEPLOYMENT.md           # Deployment guide
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint |
