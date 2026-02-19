# Claude Code Productivity Suite

**13 skills + 2 commands that turn Claude Code into your connected workspace.**

Read emails, pull meeting transcripts, manage tasks, write to Drive and Sheets, extract YouTube transcripts, analyze videos with AI, convert markdown to PDF — all by talking to Claude.

---

## What's Included

| Skill | What You Can Say to Claude |
|-------|---------------------------|
| **Gmail** | "Check my inbox", "Search for emails from [name]", "Draft a reply to this thread" |
| **Google Drive** | "Upload this file to Drive", "Search for the Q1 report", "Create a folder called Projects" |
| **Google Sheets** | "Create a tracker with columns Date, Task, Status", "Add these items to the spreadsheet" |
| **Google Docs** | "Create a Google Doc from this markdown", "Update the doc with these changes" |
| **Fireflies** | "Find the transcript from Tuesday's call", "What did we discuss with [name] last week?" |
| **ClickUp** | "What's on my plate today?", "Show tasks in [space]", "Update this task to In Progress" |
| **Apify** | "Scrape this page", "Find LinkedIn profiles for [search]", "Extract data from [URL]" |
| **Slack** | "What's happening in #general?", "Draft a message to [channel]" |
| **Model Scout** | "What's the best cheap model for summarization?", "Compare Gemini Flash vs Claude Haiku" |
| **MD to PDF** | "Convert this markdown to a PDF", "Create a professional PDF from this document" |
| **YouTube Transcript** | "Get the transcript for this video: [URL]", "Extract all transcripts from this channel" |
| **Video Understanding** | "Analyze this screen recording", "Summarize this YouTube video visually", "Document this process from the recording" |
| **Web Fallback** | "Fetch this page" (used automatically when standard fetching fails) |

> Gmail, Slack, ClickUp — **read-only by default.** No emails or messages are sent without your explicit approval.

### Commands

| Command | What It Does |
|---------|-------------|
| `/checkpoint` | Saves a structured summary of the current session to `workspace/docs/` — pick up exactly where you left off in a new session |
| `/commit` | Runs `git diff`, auto-generates a commit message, stages everything, commits, and pushes |

---

## Install

```
/plugin marketplace add riccardovandra/cc-plugin-productivity-suite
/plugin install productivity-suite@riccardovandra
```

Done. Restart Claude Code and all 13 skills and 2 commands are available.

---

## Setup

### Step 0 — Install UV (if you haven't already)

All scripts run via [UV](https://astral.sh/uv), a fast Python runtime. Install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### Step 1 — Set API Keys (5–10 minutes)

Create a `.env` file in your workspace root (or set these in your shell profile):

```bash
# Only set what you plan to use — skip the rest

FIREFLIES_API_KEY=        # Fireflies.ai → Settings → API
CLICKUP_API_KEY=          # ClickUp → Settings → Apps → API Token (starts with pk_)
APIFY_API_KEY=            # console.apify.com/account/integrations
OPENROUTER_API_KEY=       # openrouter.ai/keys
SLACK_BOT_TOKEN=          # api.slack.com/apps → OAuth & Permissions (starts with xoxb-)
SUPADATA_API_KEY=         # supadata.ai — optional fallback for YouTube transcripts
GEMINI_API_KEY=           # aistudio.google.com/apikey — required for Video Understanding
```

**Slack setup note:** You need to create a Slack App with these scopes:
`channels:read`, `channels:history`, `groups:read`, `groups:history`, `im:read`, `users:read`

---

### Step 2 — Google OAuth (20–30 minutes, one time only)

This unlocks **Gmail, Google Drive, Google Sheets, and Google Docs** in a single setup.

**Part A: Create Google Cloud credentials**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable these APIs:
   - Gmail API
   - Google Drive API
   - Google Sheets API
   - Google Docs API
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose **Desktop app**, name it anything
6. Download the JSON file
7. Save it as: `~/.claude/integrations/google/credentials/client_secrets.json`

   ```bash
   mkdir -p ~/.claude/integrations/google/credentials
   mv ~/Downloads/client_secret_*.json ~/.claude/integrations/google/credentials/client_secrets.json
   ```

8. Go to **OAuth consent screen → Test users** → add your Gmail address

**Part B: Authorize**

```bash
uv run ~/.claude/plugins/cache/riccardovandra/cc-plugin-productivity-suite/integrations/google/scripts/oauth_setup.py
```

A browser window opens. Sign in with your Google account. Done.

**Verify it worked:**

```bash
uv run ~/.claude/plugins/cache/riccardovandra/cc-plugin-productivity-suite/integrations/google/scripts/oauth_setup.py --status
```

You should see your authorized scopes listed.

---

## How to Use

Just talk to Claude. The skills activate based on what you ask:

```
"Check if I have any unread emails from clients"
"Find the Fireflies transcript from my call with [name]"
"Create a ClickUp task: 'Review proposal' in the Sales list"
"Upload this report to my Google Drive in the Client Deliverables folder"
"Convert this markdown to a PDF with the brand style"
```

No commands to memorize. Skills activate automatically. For the explicit commands, use `/checkpoint` or `/commit` at any time.

---

## Troubleshooting

### API key not found
- Check your `.env` file is in your workspace root (same folder as your CLAUDE.md)
- No spaces around `=`: `CLICKUP_API_KEY=pk_abc123` not `CLICKUP_API_KEY = pk_abc123`
- Restart Claude Code after adding keys

### Google OAuth "access blocked" error
- You must add yourself as a Test User in Google Cloud Console
- Go to **OAuth consent screen → Test users** and add your Gmail

### Google skill can't find credentials
- Verify the file exists: `ls ~/.claude/integrations/google/credentials/`
- You should see `client_secrets.json` and `token.json`
- If `token.json` is missing, run the setup again: `uv run ... oauth_setup.py`

### Skill doesn't seem to work
- Restart Claude Code (plugins are loaded at startup)
- Run `claude --version` to confirm you're on a version that supports plugins

---

## License

MIT — use freely, modify as needed, share with credit.

---

Made by [Riccardo Vandra](https://riccardovandra.com)
