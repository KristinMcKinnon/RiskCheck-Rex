# RiskCheck Rex 🦖

A **preliminary, AI-assisted risk assessment** tool for people working on
Australian government projects. It's a brainstorming starting point aligned
to ISO 31000:2018 concepts - **not** a substitute for a formal risk
assessment or professional risk practitioner judgement. Every screen carries
a disclaimer to that effect.

## How the pieces fit together

- **Streamlit** turns the Python code in this repo into the actual website
  - one form, one results page, no separate frontend/backend to build or run.
- **This GitHub repo** is what Streamlit Community Cloud watches. Push new
  code here and your live app updates automatically.
- **Streamlit Community Cloud** hosts the app for free.
- **Gemini API** (Google) is called from the server-side Python code to
  generate the risk list - your Gemini key never goes to the browser.
- **Turso** is a small free hosted database that remembers in-progress
  assessments for 30 days of inactivity, so a saved link still works if you
  come back later (Streamlit Cloud's own storage doesn't reliably survive
  restarts).

## One-time setup you need to do

You'll need three things before the app fully works: a Gemini API key, a
Turso database, and a Streamlit Cloud deployment with those two as "secrets".
None of this costs money at this tool's expected traffic level.

### 1. Get a free Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/) and sign in with
   a Google account.
2. Click **Get API key** (usually top-left) → **Create API key**.
3. Copy the key somewhere safe - you'll paste it into Streamlit's secrets
   in step 4. Don't share it or commit it anywhere.

The app uses **Gemini 2.5 Flash**, which as of today has a free-tier limit
of **10 requests/minute and 250 requests/day** - each "Generate risk
assessment" click uses one request, so 250/day is a lot of headroom for a
low-traffic internal tool. Google can change these limits over time; you can
always check current numbers in AI Studio.

### 2. Set up a free Turso database

1. Go to [turso.tech](https://turso.tech/) and click to sign up (GitHub or
   Google login).
2. In the dashboard, create a new database (any name, e.g. `riskcheck-rex`).
3. Open the database and copy its **Database URL** - it looks like
   `libsql://riskcheck-rex-yourname.turso.io`.
4. Still in the database's page, create a new **auth token** and copy it.
   Treat it like a password.

Turso's free tier (5GB storage, 500M reads/month at time of writing) is far
more than this tool will ever use, and unlike some competitors it doesn't
pause the database after inactivity, so drafts saved weeks ago are still
instantly there when someone returns.

### 3. Push this code to GitHub

This repo (`kristinmckinnon/riskcheck-rex`) already exists, so there's
nothing to create - just make sure whatever branch you want Streamlit Cloud
to deploy from (e.g. `main`) has this code merged into it.

### 4. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in
   (you can use your GitHub account).
2. Click **New app**, choose the `kristinmckinnon/riskcheck-rex` repo, pick
   the branch, and set the main file path to `app.py`.
3. Before (or after) it deploys, open the app's **Settings → Secrets** and
   paste in the following, filling in your own values from steps 1-2:

   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   TURSO_DATABASE_URL = "libsql://your-database-name.turso.io"
   TURSO_AUTH_TOKEN = "your-turso-auth-token"
   ```
4. Save. Streamlit Cloud will restart the app with those secrets available,
   and you should have a working, shareable link.

## Testing on your own computer first (optional)

If you want to try it locally before deploying:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your real keys
streamlit run app.py
```

If you leave `TURSO_DATABASE_URL` out of your local secrets file, the app
falls back to a local SQLite file under `.local_data/` automatically, so you
can test the form and Gemini call without a Turso account yet.

## What this tool deliberately does not do

- It does **not** rate or score risks (no likelihood/consequence/risk
  matrix) - that requires your organisation's own risk criteria, which this
  tool has no visibility of. It only identifies risks, opportunities, and
  suggested controls.
- It does **not** have user accounts or a login. Anyone with a specific
  assessment's link can view/edit it, so assessment IDs are long random
  strings (not sequential) and results pages ask search engines not to
  index them - but this is not a substitute for keeping genuinely sensitive
  information out of the tool in the first place (see the on-screen notice).
- Generation is capped at 50 requests/day per visitor as a safety net
  against runaway Gemini usage/cost from an open, unauthenticated link -
  not intended to affect normal use.
