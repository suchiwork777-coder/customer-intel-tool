# Customer Intelligence Tool — Deployment Guide

## What this is
A Streamlit app that helps a Customer Success Manager answer:
1. What is happening inside my customer's organisation?
2. What useful insight can I share with the customer today?

It pulls free public news signals (Google News RSS) about a company and uses
a free AI model (via Groq) to turn them into an actionable daily brief.

## Cost
$0. Every component used (Streamlit Community Cloud hosting, Google News RSS,
Groq API free tier) has a permanent free tier with no credit card required.

---

## Step-by-step deployment (10-15 minutes)

### 1. Get a free Groq API key
1. Go to https://console.groq.com and sign up (free, no card).
2. Click **API Keys** in the left menu → **Create API Key**.
3. Copy the key — you'll need it in Step 4.

### 2. Put this code on GitHub
1. Go to https://github.com and create a free account if you don't have one.
2. Click the **+** icon (top right) → **New repository**.
3. Name it `customer-intel-tool`, keep it **Public**, click **Create repository**.
4. Click **uploading an existing file** (link on the empty repo page).
5. Drag in these 3 files: `app.py`, `requirements.txt`, `README.md`.
6. Click **Commit changes**.

### 3. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** → **From existing repo**.
3. Select your `customer-intel-tool` repository, branch `main`, main file `app.py`.
4. Click **Advanced settings** → **Secrets** and paste:
   ```toml
   GROQ_API_KEY = "paste-your-groq-key-here"
   ```
5. Click **Deploy**. Wait 1-2 minutes.
6. You'll get a public URL like `https://your-app-name.streamlit.app` — this is
   your deployed application link for submission.

### 4. Test it
Open your app URL, type a well-known public company name (e.g. "Microsoft" or
"Salesforce") into the box, and click **Generate Brief**.

---

## Usage instructions for reviewers
- No login required — the app is public.
- The Groq API key is already embedded in the app's secrets, so reviewers don't
  need their own key.
- Simply enter any company name and click "Generate Brief."

## Notes on assumptions
- "Enterprise customer" is assumed to have a public online footprint (news
  coverage), which is realistic for most B2B enterprise accounts.
- The tool works best with well-known or mid-size companies; very small/private
  companies may return few signals — the app is designed to say so honestly
  rather than invent information.
