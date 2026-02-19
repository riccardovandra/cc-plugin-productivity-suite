---
name: youtube-transcript
description: Extract transcripts from YouTube videos or entire channels using yt-dlp with APIFY/Supadata fallbacks. Use when user shares a YouTube URL, asks to "get transcript", "extract from YouTube", needs video text, or wants to fetch all videos from a channel.
---

# YouTube Transcript

Extract transcripts from YouTube videos, then save to the knowledge base.

## Quick Start

```
User: "Process this video: https://youtube.com/watch?v=..."
-> Fetches transcript (waterfall: yt-dlp -> APIFY -> Supadata)
-> Categorizes video type
-> Extracts key insights
-> Saves to context/learning/
```

## Available Operations

| Operation | Description | Module |
|-----------|-------------|--------|
| Fetch Transcript | Get text from any YouTube video | [TRANSCRIPT.md](modules/TRANSCRIPT.md) |
| **Fetch Channel** | Get all transcripts from a channel | See below |
| Extract Insights | Analyze and summarize key points | [INSIGHTS.md](modules/INSIGHTS.md) |

## Scripts

### Single Video

Fetch transcript:
```bash
uv run .claude/skills/youtube-transcript/scripts/youtube_transcript.py <url>
```

With timestamps:
```bash
uv run .claude/skills/youtube-transcript/scripts/youtube_transcript.py <url> --timestamps
```

Verbose mode (see which service was used):
```bash
uv run .claude/skills/youtube-transcript/scripts/youtube_transcript.py <url> --verbose
```

JSON output:
```bash
uv run .claude/skills/youtube-transcript/scripts/youtube_transcript.py <url> --json
```

### Entire Channel

Fetch all transcripts from a channel:
```bash
uv run .claude/skills/youtube-transcript/scripts/fetch_channel.py https://www.youtube.com/@channelname
```

Limit to most recent N videos:
```bash
uv run .claude/skills/youtube-transcript/scripts/fetch_channel.py https://www.youtube.com/@channelname --limit 10
```

With timestamps and skip existing:
```bash
uv run .claude/skills/youtube-transcript/scripts/fetch_channel.py https://www.youtube.com/@channelname \
    --timestamps --skip-existing
```

Custom output directory:
```bash
uv run .claude/skills/youtube-transcript/scripts/fetch_channel.py https://www.youtube.com/@channelname \
    --output ./workspace/research/channel-transcripts
```

### Channel Fetch Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--limit` | None | Limit to most recent N videos |
| `--output` | workspace/docs/{date} - {channel} Transcripts | Output directory |
| `--timestamps` | false | Include timestamps in transcripts |
| `--skip-existing` | false | Skip videos with existing transcripts |
| `--concurrency` | 3 | Parallel transcript fetches |

**Output structure:**
```
workspace/docs/YYYY-MM-DD - {channel} Transcripts/
├── _manifest.json           # Fetch summary with all video statuses
├── Video-Title-1_abc123.txt # Transcript with metadata header
├── Video-Title-2_def456.txt
└── ...
```

## Transcript Waterfall

The script tries multiple services in order for maximum reliability:

| Priority | Service | Type | Cost | Notes |
|----------|---------|------|------|-------|
| 1 | yt-dlp | CLI | Free | Local, fast, requires installation |
| 2 | APIFY | Cloud | ~$0.10/1K | Requires APIFY_API_KEY |
| 3 | Supadata | API | Paid | Requires SUPADATA_API_KEY |

If yt-dlp fails (video has no subtitles, etc.), it automatically falls back to APIFY, then Supadata.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| APIFY_API_KEY | Optional | For APIFY fallback |
| SUPADATA_API_KEY | Optional | For Supadata fallback |

If only yt-dlp is available, the script still works for most videos.

## Requirements

**System:**
```bash
brew install yt-dlp
# or: pip install yt-dlp
```

**Python packages:**
```bash
pip install -r .claude/skills/youtube-transcript/scripts/requirements.txt
```

## Workflow

1. **Get Transcript** - Run script (uses waterfall internally)
2. **Categorize** - Identify video type (Tutorial, Interview, Course, Analysis, Case Study)
3. **Extract** - Pull insights based on type
4. **Connect** - Link to existing knowledge
5. **Save** - Store in `context/learning/{topic}/`

## Output Location

All insights saved to: `context/learning/{topic}/{video-title}.md`
