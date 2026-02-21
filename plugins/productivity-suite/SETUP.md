# Productivity Suite — Guided Setup

> **How to use this file:** Share it with Claude Code and say:
> *"Please guide me through setting up the Productivity Suite step by step. Check each step before moving to the next."*
>
> Claude will read this file and walk you through every step interactively.

---

## What You're Installing

13 skills that let you control Gmail, Google Drive, Sheets, Docs, Fireflies, ClickUp, Apify, Slack, YouTube, and more — just by talking to Claude.

**Setup takes about 30–45 minutes total.** Most of it is one-time Google OAuth setup. The rest is copying API keys.

---

## Step 0: Check Prerequisites

Before anything else, check that these are installed:

**Check UV (Python runner):**
```bash
uv --version
```

If you see a version number, UV is installed. If you get "command not found":
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then close and reopen your terminal.

**Check Claude Code:**
```bash
claude --version
```

If you get "command not found", install Claude Code from [claude.ai/code](https://claude.ai/code).

---

## Step 1: Install the Plugin

### If you're using Claude Code in the terminal:

Run these two commands inside Claude Code (not in a regular terminal):
```
/plugin marketplace add riccardovandra/cc-plugin-productivity-suite
/plugin install productivity-suite@riccardovandra
```

Then restart Claude Code.

### If you're using the VS Code extension:

1. Type `/plugins` in the Claude chat
2. Go to **Marketplace**
3. Add this link: `https://github.com/riccardovandra/cc-plugin-productivity-suite`
4. Select the plugins you want to install
5. Restart VS Code.

**Verify installation:** Ask Claude: *"What skills do you have available?"* — it should list Gmail, Slack, ClickUp, etc.

---

## Step 2: Set API Keys

You only need to set keys for the tools you plan to use. Skip any you don't use.

### Where to put them

Create or edit a `.env` file in your **project root** (the folder where your CLAUDE.md lives, or the folder you open in VS Code). The file should look like this:

```bash
FIREFLIES_API_KEY=your_key_here
CLICKUP_API_KEY=your_key_here
APIFY_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
SLACK_BOT_TOKEN=your_token_here
SUPADATA_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

No spaces around `=`. No quotes needed.

### Where to get each key

**Fireflies** (meeting transcripts):
1. Go to [fireflies.ai](https://fireflies.ai) → log in
2. Click your profile photo → Settings → API
3. Copy the API key

**ClickUp** (task management):
1. Go to [app.clickup.com](https://app.clickup.com) → log in
2. Click your profile photo → Settings → Apps → API Token
3. Copy the token (starts with `pk_`)

**Apify** (web scraping):
1. Go to [console.apify.com](https://console.apify.com) → log in
2. Click your profile photo → Settings → Integrations
3. Copy your API key

**OpenRouter** (AI model routing, used by Model Scout):
1. Go to [openrouter.ai/keys](https://openrouter.ai/keys) → log in
2. Click "Create Key"
3. Copy the key

**Gemini** (required for Video Understanding):
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → log in
2. Click "Create API Key"
3. Copy the key

**Supadata** (optional fallback for YouTube transcripts):
1. Go to [supadata.ai](https://supadata.ai) → sign up
2. Copy your API key from the dashboard

**Slack** (reading messages and drafting):
This one requires a few more steps — see the Slack section below.

### Slack App Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → click "Create New App"
2. Choose "From scratch" → name it anything (e.g. "Claude Assistant") → select your workspace
3. Go to **OAuth & Permissions** → scroll to **Scopes** → under **Bot Token Scopes**, add:
   - `channels:read`
   - `channels:history`
   - `groups:read`
   - `groups:history`
   - `im:read`
   - `users:read`
4. Click **Install to Workspace** (top of the OAuth page)
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
6. Add it to your `.env` file as `SLACK_BOT_TOKEN=xoxb-...`
7. In Slack, invite your bot to any channels you want Claude to read (type `/invite @YourBotName` in the channel)

---

## Step 3: Google OAuth Setup

This is a one-time setup that unlocks Gmail, Google Drive, Google Sheets, and Google Docs all at once.

**Total time: about 20–30 minutes.**

### Part A: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. If you've never used it before: click "Select a project" at the top → "New Project" → give it any name (e.g. "Claude Integration") → click "Create"
3. Make sure your new project is selected at the top

### Part B: Enable the APIs

1. In the left sidebar, go to **APIs & Services → Library**
2. Search for and enable each of these (click the API name → click "Enable"):
   - **Gmail API**
   - **Google Drive API**
   - **Google Sheets API**
   - **Google Docs API**

### Part C: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth 2.0 Client ID**
3. If prompted to configure the consent screen first:
   - Choose "External" → fill in the required fields (App name: anything, Support email: your email) → click Save
4. For Application type, choose: **Desktop app**
5. Name it anything (e.g. "Claude Code")
6. Click "Create"
7. Click the **Download** button (arrow icon) next to the client you just created
8. Move the downloaded file to the right location:
   ```bash
   mkdir -p ~/.claude/integrations/google/credentials
   mv ~/Downloads/client_secret_*.json ~/.claude/integrations/google/credentials/client_secrets.json
   ```
   Verify it's there:
   ```bash
   ls ~/.claude/integrations/google/credentials/
   ```
   You should see `client_secrets.json`.

### Part D: Add Yourself as a Test User

1. Go to **APIs & Services → OAuth consent screen**
2. Scroll down to **Test users** → click **+ Add Users**
3. Enter your Gmail address → click Save

### Part E: Authorize

Run this command in your terminal:

```bash
uv run ~/.claude/integrations/google/scripts/oauth_setup.py
```

A browser window will open. Sign in with the same Gmail you added as a test user. Click "Allow" on the permissions screen.

If you installed via the CLI plugin system, the path is:
```bash
uv run ~/.claude/plugins/cache/riccardovandra/cc-plugin-productivity-suite/integrations/google/scripts/oauth_setup.py
```

**Verify it worked:**
```bash
uv run ~/.claude/integrations/google/scripts/oauth_setup.py --status
```
You should see a list of authorized scopes (Gmail, Drive, Sheets, Docs).

---

## Step 4: Test It

After restarting Claude Code, try these prompts one by one:

**Gmail:**
> "Check my inbox and show me the 5 most recent unread emails."

**Google Drive:**
> "List the most recent files in my Google Drive."

**ClickUp:**
> "What are my open tasks in ClickUp?"

**Fireflies:**
> "Show me my recent meeting transcripts from Fireflies."

**Slack:**
> "List my Slack channels."

**YouTube Transcript:**
> "Get the transcript for this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

If anything doesn't work, check the Troubleshooting section in README.md.

---

## Done

All 13 skills are now available. Just talk to Claude naturally — no commands to memorize.

**What works now:**
- Gmail: read, search, sort, draft
- Google Drive: search, upload, create folders
- Google Sheets: create, read, update, import CSV
- Google Docs: create from markdown, update
- Fireflies: search and retrieve meeting transcripts
- ClickUp: browse tasks, update status, read comments
- Apify: web scraping and data extraction
- Slack: read channels, draft messages
- Model Scout: compare AI models
- MD to PDF: convert markdown to PDF
- YouTube Transcript: extract video transcripts
- Video Understanding: analyze videos with Gemini
- Web Fallback: alternative web fetching

**Commands available:**
- `/checkpoint` — save session state for continuity
- `/commit` — auto-generate a commit message and push
