# Transcript Module

Fetch transcripts from YouTube videos using a multi-service waterfall.

---

## When to Use

- User provides a YouTube URL
- User asks for "transcript" or "captions"
- Need text content before insight extraction

---

## Script Usage

**Basic (plain text):**
```bash
uv run .claude/skills/youtube/scripts/youtube_transcript.py <url>
```

**With timestamps:**
```bash
uv run .claude/skills/youtube/scripts/youtube_transcript.py <url> --timestamps
```

**Verbose (show service used):**
```bash
uv run .claude/skills/youtube/scripts/youtube_transcript.py <url> --verbose
```

**JSON output:**
```bash
uv run .claude/skills/youtube/scripts/youtube_transcript.py <url> --json
```

**Examples:**
```bash
# Full URL
uv run .claude/skills/youtube/scripts/youtube_transcript.py "https://www.youtube.com/watch?v=JlbzZiBADlw"

# Short URL
uv run .claude/skills/youtube/scripts/youtube_transcript.py "https://youtu.be/JlbzZiBADlw"

# Just video ID
uv run .claude/skills/youtube/scripts/youtube_transcript.py JlbzZiBADlw
```

---

## Service Waterfall

The script tries services in this order:

### 1. yt-dlp (Primary)
- **Type:** Local CLI tool
- **Cost:** Free
- **Speed:** Fast (1-5 seconds)
- **Reliability:** High for videos with captions
- **Install:** `brew install yt-dlp`

### 2. APIFY (Secondary)
- **Type:** Cloud scraper
- **Cost:** ~$0.10 per 1000 requests
- **Speed:** 5-30 seconds
- **Reliability:** Handles edge cases yt-dlp misses
- **Requires:** `APIFY_API_KEY` in .env

### 3. Supadata (Tertiary)
- **Type:** API service
- **Cost:** Paid per request
- **Speed:** 5-60 seconds (async for long videos)
- **Reliability:** Most comprehensive
- **Requires:** `SUPADATA_API_KEY` in .env

---

## Output Formats

**Plain text (default):**
```
Welcome to this video about AI automation...
Today we'll cover three main topics...
```

**With timestamps:**
```
[00:00] Welcome to this video about AI automation...
[00:15] Today we'll cover three main topics...
[01:30] First, let's talk about workflows...
```

**JSON output:**
```json
{
  "video_id": "abc123",
  "source": "ytdlp",
  "language": "en",
  "text": "Full transcript...",
  "segments": [
    {"text": "Welcome...", "start": 0.0, "duration": 5.2}
  ]
}
```

---

## Language Handling

The script tries languages in order:
1. English (en, en-US, en-GB)
2. Any available language (fallback)

Most videos have auto-generated captions even if manual ones aren't available.

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Could not extract video ID" | Invalid URL format | Check URL is valid YouTube link |
| "All services failed" | No captions on any service | Ask user to paste transcript manually |
| "yt-dlp not installed" | Missing CLI tool | Install with `brew install yt-dlp` |
| "API key not configured" | Missing env var | Add keys to .env |

**When all services fail:**
Ask the user:
> "I couldn't fetch the transcript automatically (tried yt-dlp, APIFY, Supadata). Could you paste the transcript or provide a different video URL?"

---

## Debugging

Use `--verbose` to see which service succeeded:
```
$ python youtube_transcript.py "https://youtube.com/watch?v=abc123" --verbose
Attempting yt-dlp...
yt-dlp failed: No subtitles found
Attempting APIFY...
Success via APIFY
```

---

## Next Steps

After fetching transcript:
1. Proceed to [INSIGHTS.md](INSIGHTS.md) for extraction
2. Or return raw transcript to user if that's all they need
