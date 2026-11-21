# Cloud Deployment Guide: Manyavar Stock Move Recommender

This guide explains how to deploy the repository (`https://github.com/TumAro/VCH3`) to cloud Platform-as-a-Service (PaaS) providers for live demonstrations and evaluations.

---

## Method 1: Deploy to Render (Recommended — Free & Automatic)

[Render](https://render.com/) offers a free tier for Docker web services with automatic builds from GitHub.

### Step-by-Step Instructions:
1. **Sign in to Render:**
   - Go to [dashboard.render.com](https://dashboard.render.com/) and sign in using your GitHub account (`TumAro`).
2. **Create a New Web Service:**
   - Click the **New +** button in the top right and select **Web Service**.
   - Select **Build and deploy from a Git repository**.
3. **Connect Repository:**
   - Choose the repository `TumAro/VCH3` (or paste the repository URL).
4. **Configure Service:**
   - **Name:** `manyavar-recommender` (or your preferred name).
   - **Region:** Singapore or Frankfurt (choose nearest to evaluators).
   - **Branch:** `main`.
   - **Runtime:** `Docker` (Render will detect the `Dockerfile` in the root).
   - **Instance Type:** `Free`.
5. **Environment Variables:**
   - No extra environment variables are required. Render automatically sets `PORT=10000` (which `run.py` detects).
6. **Deploy:**
   - Click **Create Web Service**.
   - Render will build the Docker container and start Uvicorn.
   - Once the log shows `Application startup complete`, your public URL (e.g. `https://manyavar-recommender.onrender.com`) will be active.

> **Note on Free Tier Sleep:** Render's free tier spins down after 15 minutes of inactivity. When someone visits the URL after inactivity, it may take 30-45 seconds to wake up.

---

## Method 2: Deploy to Railway

[Railway](https://railway.app/) provides high-speed deployments with generous trial credits.

### Step-by-Step Instructions:
1. **Sign in to Railway:**
   - Visit [railway.app](https://railway.app/) and sign in with GitHub.
2. **Create New Project:**
   - Click **New Project** -> **Deploy from GitHub repo**.
   - Select `TumAro/VCH3`.
3. **Automatic Detection:**
   - Railway immediately detects the `Dockerfile` and triggers the build.
4. **Generate Public Domain:**
   - Click on the deployed service card -> go to **Settings** -> **Networking** -> **Public Networking**.
   - Click **Generate Domain**.
   - Your service is live at `https://<service-name>.up.railway.app`.

---

## Method 3: Deploy to Fly.io

For fast CLI-based global deployments:

```bash
# 1. Install flyctl
# (Windows: powershell -Command "iwr https://fly.io/install.ps1 -useb | iex")

# 2. Login
fly auth login

# 3. Launch from repository directory
fly launch --name manyavar-recommender --region sin

# 4. Deploy
fly deploy
```

---

## Verifying the Deployment

Once deployed, visit your assigned public URL:
1. **Overview Tab:** Confirm network totals, state revenue breakdown, and monthly revenue trends load.
2. **Moves Tab:** Confirm the 54 approved stock moves render with filters, rationales, and "Needs sign-off" badge.
3. **Export Check:** Click **Export CSV** and **Export Excel** to confirm downloads trigger successfully over HTTPS.
