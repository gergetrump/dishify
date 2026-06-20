# Dishify Web Client

React web client for the Dishify backend gateway.

## Setup

```bash
cd web-client
cp .env.example .env
npm install
npm run dev
```

The app expects the backend gateway at `VITE_API_URL`, which defaults to `http://localhost:8000`.

## Backend

From the repo root:

```bash
docker compose up -d
docker compose run --rm indexing-worker --recreate
```

Then visit `http://localhost:5173`.
