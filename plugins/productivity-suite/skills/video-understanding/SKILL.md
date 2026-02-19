---
name: Video Understanding
description: Analyze videos using Gemini's native video understanding. Watch videos and extract summaries, step-by-step processes, or visual element descriptions. Supports local files and YouTube URLs. Use when user mentions video analysis, watch video, understand video, extract from video, video summary, screen recording analysis, process documentation from video, or analyze YouTube video.
---

# Video Understanding

Analyze videos using Google Gemini's native video understanding capability. Supports both **local video files** and **YouTube URLs**.

## Prerequisites

**Environment variable required:**
- `GEMINI_API_KEY` - Google AI Studio API key (add to `.env`)

Get your API key at: https://aistudio.google.com/apikey

## Limits

| Limit | Value |
|-------|-------|
| **File size** | 100MB inline, larger via Files API (automatic) |
| **Duration** | 1 hour (default), 3 hours (low resolution) |
| **Token usage** | ~300 tokens/sec (default), ~100 tokens/sec (low res) |
| **Formats** | mp4, mov, avi, webm, mpeg, wmv, flv, 3gpp |

## Usage

### Local Video File

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py video.mp4
```

### YouTube URL

```bash
# Analyze a YouTube video directly
uv run .claude/skills/video-understanding/scripts/analyze_video.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Also supports short URLs
uv run .claude/skills/video-understanding/scripts/analyze_video.py "https://youtu.be/VIDEO_ID"
```

### Analysis Modes

| Mode | Use When |
|------|----------|
| `summary` (default) | General video understanding - key moments, topics, takeaways |
| `process` | Screen recordings - extract step-by-step documentation |
| `visual` | Describe what's shown - people, objects, UI, text on screen |

```bash
# Summary mode (default)
uv run .claude/skills/video-understanding/scripts/analyze_video.py video.mp4

# Process extraction for screen recordings
uv run .claude/skills/video-understanding/scripts/analyze_video.py recording.mp4 --mode process

# Visual elements description
uv run .claude/skills/video-understanding/scripts/analyze_video.py video.mp4 --mode visual
```

### Save to File

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py video.mp4 -o analysis.md
```

### Long Videos (Low Resolution)

For videos over 1 hour (up to 3 hours):

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py long_video.mp4 --low-res
```

## Mode Details

### Summary Mode (Default)

Best for general video understanding. Returns:
- Overview (2-3 sentence summary)
- Key moments with timestamps
- Main topics covered
- Key takeaways

### Process Mode

Best for screen recordings and software walkthroughs. Returns:
- Process overview
- Prerequisites
- Step-by-step instructions (numbered, with specific UI actions)
- Data fields involved
- Decision points
- Automation notes

### Visual Mode

Best for understanding what's shown in a video. Returns:
- Scene overview
- People descriptions
- Objects and elements
- UI elements (if software)
- Scene changes with timestamps
- Text visible on screen

## Examples

### Example 1: Summarize a Tutorial Video

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py tutorial.mp4 -o summary.md
```

### Example 2: Document a CRM Process

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py "CRM walkthrough.mp4" --mode process -o process-doc.md
```

### Example 3: Analyze What's in a Video

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py presentation.mp4 --mode visual
```

### Example 4: Deep Dive on a YouTube Video

```bash
uv run .claude/skills/video-understanding/scripts/analyze_video.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o deep-dive.md
```

## YouTube Research Workflow

For researching videos from a channel:

1. **Discover videos** - Use `youtube-transcript` skill to fetch channel videos
2. **Quick scan** - Get transcripts and review topics
3. **Deep dive** - Use this skill on specific videos that interest you

```bash
# Step 1: Get channel videos (youtube-transcript skill)
uv run .claude/skills/youtube-transcript/scripts/fetch_channel.py CHANNEL_ID

# Step 2: Get transcript for quick review (youtube-transcript skill)
uv run .claude/skills/youtube-transcript/scripts/youtube_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Step 3: Deep visual analysis on interesting videos (this skill)
uv run .claude/skills/video-understanding/scripts/analyze_video.py "https://youtube.com/watch?v=VIDEO_ID" -o analysis.md
```

## Technical Notes

- Uses `gemini-2.5-flash` by default (best video quality, cost-effective)
- **Local files**: Uploaded to Gemini temporarily, deleted after analysis
- **YouTube URLs**: Passed directly to Gemini (no download/upload needed)
- Processing time depends on video length (typically 5-30 seconds)
- Gemini 2.0 is being retired March 2026, hence 2.5 is the default
