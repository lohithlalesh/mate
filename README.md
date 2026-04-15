# Simplify Suite Tweet Generator

Automatically fetches SaaS/business news, filters for relevance, and generates brand-voice tweets.
Results land in `tweets_queue.xlsx` inside this repo — you review, you post.

---

## How to Turn It ON / OFF

| Action | How |
|---|---|
| **Turn ON** | Go to your repo → **Actions** tab → click `Simplify Suite — Tweet Generator` → click **Enable workflow** |
| **Turn OFF** | Same place → click **Disable workflow** |
| **Run it right now** | Actions tab → select workflow → **Run workflow** button (top right) |

When ON it runs automatically every 4 hours and commits updated `tweets_queue.xlsx` to the repo.

---

## One-Time Setup (5 minutes)

### Step 1 — Create the GitHub repo

1. Go to github.com → New repository
2. Name it `simplify-tweet-bot` (or anything)
3. Set to **Private**
4. Don't add any files yet

### Step 2 — Upload these files

Upload the following files to the repo root (drag and drop on GitHub works):
```
generate_tweets.py
requirements.txt
README.md
.github/
  workflows/
    tweet_generator.yml
```

### Step 3 — Add your Gemini API key

1. Get your free API key from: https://aistudio.google.com/app/apikey
2. In your GitHub repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. Name: `GEMINI_API_KEY`
4. Value: paste your key
5. Click **Add secret**

### Step 4 — Enable the workflow

1. Go to **Actions** tab in your repo
2. You'll see `Simplify Suite — Tweet Generator`
3. Click **Enable workflow** if prompted
4. Click **Run workflow** to test it immediately

### Step 5 — Get your tweets

After the first run (takes ~2 minutes):
- Go to your repo's file list
- Download `tweets_queue.xlsx`
- Or just view it in the **Code** tab — GitHub renders Excel files

---

## What the XLSX looks like

| Tweet Text | Source | Article Title | Source URL | Generated At | Status | Notes |
|---|---|---|---|---|---|---|
| Your ready-to-post tweet | TechCrunch | Article title | https://... | 2026-04-15 08:00 UTC | *(blank)* | *(your notes)* |

**Your workflow:**
1. Open `tweets_queue.xlsx` each morning
2. Review the tweets (edit if needed)
3. Copy-paste your favourites to Twitter/X
4. Mark the **Status** column as `posted` so you know what's been used

---

## RSS Sources It Monitors

- TechCrunch
- SaaStr
- G2 Learn
- The Verge
- Entrepreneur
- Product Hunt
- Hacker News

Topics it filters for: SaaS tools, business software, project management, small team ops, competitor news (monday.com, ClickUp, Asana, Notion, Rippling, Zoho, etc.), AI in business, subscription costs, tool fatigue.

---

## Cost

| Item | Cost |
|---|---|
| Gemini Flash API | **Free** (1,500 requests/day limit — you'll use ~50/day) |
| GitHub Actions | **Free** (2,000 minutes/month — you'll use ~30 minutes/day) |
| **Total** | **$0/month** |

---

## Customising the Brand Voice

Open `generate_tweets.py` and edit the `TWEET_PROMPT` string (line ~60).
The current prompt is tuned for Simplify Suite's voice — direct, sharp, anti-complexity.
