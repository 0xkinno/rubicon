# Deployment Architecture & Production Guide

This guide details the dual production deployment configuration for **RUBICON**:
1. **Frontend**: Next.js 14 Web Console on Vercel
2. **Backend**: FastAPI Deterministic Engine & Receipt Server on Render

---

## 1. Frontend: Next.js 14 on Vercel

The frontend located in `app/web` is an edge-optimized Next.js 14 console featuring the Rubicon Boundary Visualizer, Reversibility Desk, and Cryptographic Receipt Inspector.

### Vercel Project Settings

- **Framework Preset**: Next.js
- **Root Directory**: `app/web`
- **Build Command**: `next build`
- **Output Directory**: `.next`
- **Node.js Version**: 18.x or 20.x

### Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `NEXT_PUBLIC_RUBICON_API_URL` | Optional | URL of the live backend API | `https://rubicon-api.onrender.com` |

> If `NEXT_PUBLIC_RUBICON_API_URL` is omitted, the console operates in autonomous client-side fallback mode with static proof manifests from `proof/results.json`.

---

## 2. Backend: FastAPI on Render

The backend located in `app/api` serves the deterministic classification engine, receipts ledger, and adapter status endpoints.

### Render Blueprint Deployment (`render.yaml`)

RUBICON includes a root `render.yaml` infrastructure-as-code specification.

1. Connect your GitHub repository to Render (`https://dashboard.render.com`).
2. Select **New** > **Blueprint**.
3. Select the `rubicon` repository.
4. Render will parse `render.yaml` and provision the Web Service.

### Manual Configuration on Render

If creating a Web Service manually:
- **Environment**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Free / Starter
- **Environment Variables**:
  - `PYTHON_VERSION`: `3.11.8`
  - `RUBICON_ENV`: `production`

---

## 3. High-Integrity Offline Mode (Zero Cloud Dependency)

In accordance with Rubicon's core design invariant:
> **The API-deletion test**: The core deterministic classifier, Ed25519 one-use permit fence, and post-rollback independent verifier require **zero** external network connectivity or cloud services.

All security guarantees, benchmark verification scripts (`make proof`), and unit test suites (`pytest`) execute completely offline in any local CI or workstation environment.
