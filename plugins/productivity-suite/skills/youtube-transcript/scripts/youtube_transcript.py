#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
YouTube Transcript Fetcher with Waterfall Fallback

Tries multiple services in order:
1. yt-dlp (free, local)
2. APIFY (cloud scraper)
3. Supadata (API service)

Usage:
    python youtube_transcript.py <video_url_or_id>
    python youtube_transcript.py <url> --timestamps
    python youtube_transcript.py <url> --verbose
    python youtube_transcript.py <url> --json
"""

import argparse
import asyncio
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# === CONFIGURATION ===

APIFY_ACTOR_ID = "karamelo~youtube-transcripts"
APIFY_API_BASE = "https://api.apify.com/v2"
SUPADATA_API_BASE = "https://api.supadata.ai/v1"

PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]

VERBOSE = False


# === DATA STRUCTURES ===

@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    video_id: str
    source: str  # "ytdlp" | "apify" | "supadata"
    language: str
    text: str
    segments: list


# === EXCEPTIONS ===

class TranscriptError(Exception):
    pass


class TranscriptNotFoundError(TranscriptError):
    pass


# === UTILITY FUNCTIONS ===

def log(message: str) -> None:
    """Print to stderr if verbose mode is enabled."""
    if VERBOSE:
        print(message, file=sys.stderr)


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract video ID from URL or return as-is if already an ID."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


def load_env_file() -> None:
    """Load .env from multiple locations."""
    locations = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent.parent.parent / ".env",
        Path.home() / "Coding" / "The Crucible" / ".env",
    ]
    for loc in locations:
        if loc.exists():
            with open(loc) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"\''))
            return


# === SERVICE 1: YT-DLP ===

def check_ytdlp_available() -> bool:
    """Check if yt-dlp is installed."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def parse_vtt_content(content: str) -> tuple[str, list[TranscriptSegment]]:
    """Parse VTT subtitle content into text and segments."""
    segments = []
    lines = content.split('\n')

    current_start = 0.0
    current_text = []
    seen_texts = set()  # Deduplicate

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Match timestamp line: 00:00:00.000 --> 00:00:05.000
        timestamp_match = re.match(
            r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})',
            line
        )
        if not timestamp_match:
            # Also try format without hours: 00:00.000 --> 00:05.000
            timestamp_match = re.match(
                r'(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2})\.(\d{3})',
                line
            )

        if timestamp_match:
            groups = timestamp_match.groups()
            if len(groups) == 8:
                # Full format with hours
                start_secs = int(groups[0]) * 3600 + int(groups[1]) * 60 + int(groups[2]) + int(groups[3]) / 1000
                end_secs = int(groups[4]) * 3600 + int(groups[5]) * 60 + int(groups[6]) + int(groups[7]) / 1000
            else:
                # Short format without hours
                start_secs = int(groups[0]) * 60 + int(groups[1]) + int(groups[2]) / 1000
                end_secs = int(groups[3]) * 60 + int(groups[4]) + int(groups[5]) / 1000

            current_start = start_secs
            duration = end_secs - start_secs

            # Get text lines until empty line
            i += 1
            text_parts = []
            while i < len(lines) and lines[i].strip():
                text_line = lines[i].strip()
                # Remove VTT formatting tags
                text_line = re.sub(r'<[^>]+>', '', text_line)
                if text_line:
                    text_parts.append(text_line)
                i += 1

            if text_parts:
                text = ' '.join(text_parts)
                # Deduplicate (YouTube often repeats captions)
                if text not in seen_texts:
                    seen_texts.add(text)
                    segments.append(TranscriptSegment(
                        text=text,
                        start=current_start,
                        duration=duration
                    ))
        i += 1

    full_text = ' '.join(seg.text for seg in segments)
    return full_text, segments


async def fetch_via_ytdlp(video_id: str, languages: list[str]) -> Optional[TranscriptResult]:
    """Fetch transcript using yt-dlp CLI."""
    if not check_ytdlp_available():
        log("yt-dlp not installed, skipping...")
        return None

    log("Attempting yt-dlp...")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Build language preference string
        lang_str = ",".join(languages)

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", lang_str,
            "--sub-format", "vtt/srt/best",
            "--convert-subs", "vtt",
            "-o", output_template,
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                log(f"yt-dlp failed: {result.stderr[:200]}")
                return None

            # Find the subtitle file
            vtt_files = list(Path(tmpdir).glob("*.vtt"))
            if not vtt_files:
                log("yt-dlp: No subtitle files found")
                return None

            # Use the first available subtitle file
            vtt_file = vtt_files[0]
            content = vtt_file.read_text(encoding='utf-8')

            # Detect language from filename (e.g., video_id.en.vtt)
            lang = "en"
            lang_match = re.search(r'\.([a-z]{2}(?:-[A-Z]{2})?)\.vtt$', vtt_file.name)
            if lang_match:
                lang = lang_match.group(1)

            full_text, segments = parse_vtt_content(content)

            if not segments:
                log("yt-dlp: Could not parse subtitles")
                return None

            log(f"Success via yt-dlp ({len(segments)} segments)")

            return TranscriptResult(
                video_id=video_id,
                source="ytdlp",
                language=lang,
                text=full_text,
                segments=[asdict(s) for s in segments]
            )

        except subprocess.TimeoutExpired:
            log("yt-dlp: Timeout")
            return None
        except Exception as e:
            log(f"yt-dlp error: {e}")
            return None


# === SERVICE 2: APIFY ===

async def fetch_via_apify(video_id: str, api_key: str) -> Optional[TranscriptResult]:
    """Fetch transcript using APIFY actor."""
    try:
        import aiohttp
    except ImportError:
        log("aiohttp not installed, skipping APIFY...")
        return None

    log("Attempting APIFY...")

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Start actor run
    run_url = f"{APIFY_API_BASE}/acts/{APIFY_ACTOR_ID}/runs?token={api_key}"

    run_input = {
        "urls": [url],
        "maxRetries": 3
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Start the run
            async with session.post(run_url, json=run_input) as resp:
                if resp.status != 201:
                    log(f"APIFY: Failed to start actor ({resp.status})")
                    return None
                run_data = await resp.json()

            run_id = run_data.get("data", {}).get("id")
            if not run_id:
                log("APIFY: No run ID returned")
                return None

            # Poll for completion (max 90 seconds)
            status_url = f"{APIFY_API_BASE}/actor-runs/{run_id}?token={api_key}"
            for _ in range(30):  # 30 * 3s = 90s max
                await asyncio.sleep(3)
                async with session.get(status_url) as resp:
                    if resp.status != 200:
                        continue
                    status_data = await resp.json()
                    status = status_data.get("data", {}).get("status")

                    if status == "SUCCEEDED":
                        break
                    elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                        log(f"APIFY: Actor run {status}")
                        return None
            else:
                log("APIFY: Timeout waiting for actor")
                return None

            # Get results from dataset
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                log("APIFY: No dataset ID")
                return None

            dataset_url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items?token={api_key}"
            async with session.get(dataset_url) as resp:
                if resp.status != 200:
                    log(f"APIFY: Failed to get dataset ({resp.status})")
                    return None
                items = await resp.json()

            if not items:
                log("APIFY: No results in dataset")
                return None

            # Extract transcript from first result
            item = items[0]
            transcript_data = item.get("transcript") or item.get("captions") or item.get("subtitles")

            if not transcript_data:
                log("APIFY: No transcript in response")
                return None

            # Handle different response formats
            if isinstance(transcript_data, str):
                full_text = html.unescape(transcript_data)
                segments = []
            elif isinstance(transcript_data, list):
                segments = []
                for entry in transcript_data:
                    if isinstance(entry, dict):
                        segments.append({
                            "text": html.unescape(entry.get("text", "")),
                            "start": float(entry.get("start", entry.get("offset", 0))),
                            "duration": float(entry.get("duration", entry.get("dur", 0)))
                        })
                    elif isinstance(entry, str):
                        segments.append({"text": html.unescape(entry), "start": 0, "duration": 0})
                full_text = ' '.join(s["text"] for s in segments)
            else:
                full_text = html.unescape(str(transcript_data))
                segments = []

            log(f"Success via APIFY")

            return TranscriptResult(
                video_id=video_id,
                source="apify",
                language=item.get("language", "en"),
                text=full_text,
                segments=segments
            )

    except Exception as e:
        log(f"APIFY error: {e}")
        return None


# === SERVICE 3: SUPADATA ===

async def fetch_via_supadata(video_id: str, api_key: str) -> Optional[TranscriptResult]:
    """Fetch transcript using Supadata API."""
    try:
        import aiohttp
    except ImportError:
        log("aiohttp not installed, skipping Supadata...")
        return None

    log("Attempting Supadata...")

    url = f"https://www.youtube.com/watch?v={video_id}"

    headers = {
        "x-api-key": api_key
    }

    params = {
        "url": url,
        "text": "true"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SUPADATA_API_BASE}/youtube/transcript",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:

                if resp.status == 202:
                    # Async job - poll for result
                    job_data = await resp.json()
                    job_id = job_data.get("jobId")

                    if not job_id:
                        log("Supadata: No job ID returned")
                        return None

                    # Poll for completion
                    for _ in range(20):  # 20 * 3s = 60s max
                        await asyncio.sleep(3)
                        async with session.get(
                            f"{SUPADATA_API_BASE}/youtube/transcript/{job_id}",
                            headers=headers
                        ) as poll_resp:
                            if poll_resp.status == 200:
                                data = await poll_resp.json()
                                if data.get("status") == "completed":
                                    resp_data = data
                                    break
                    else:
                        log("Supadata: Job timeout")
                        return None
                elif resp.status == 200:
                    resp_data = await resp.json()
                else:
                    log(f"Supadata: API error ({resp.status})")
                    return None

            # Extract transcript
            content = resp_data.get("content") or resp_data.get("transcript") or resp_data.get("text")

            if not content:
                log("Supadata: No transcript in response")
                return None

            # Handle structured vs plain text response
            if isinstance(content, list):
                segments = []
                for entry in content:
                    segments.append({
                        "text": html.unescape(entry.get("text", "")),
                        "start": float(entry.get("start", entry.get("offset", 0))),
                        "duration": float(entry.get("duration", 0))
                    })
                full_text = ' '.join(s["text"] for s in segments)
            else:
                full_text = html.unescape(str(content))
                segments = []

            log("Success via Supadata")

            return TranscriptResult(
                video_id=video_id,
                source="supadata",
                language=resp_data.get("lang", "en"),
                text=full_text,
                segments=segments
            )

    except Exception as e:
        log(f"Supadata error: {e}")
        return None


# === WATERFALL ORCHESTRATION ===

async def fetch_transcript_waterfall(
    video_id: str,
    languages: list[str] = None
) -> TranscriptResult:
    """Try each service in sequence until one succeeds."""
    if languages is None:
        languages = PREFERRED_LANGUAGES

    errors = []

    # 1. Try yt-dlp (free, local)
    result = await fetch_via_ytdlp(video_id, languages)
    if result:
        return result
    errors.append("yt-dlp: No subtitles found or tool unavailable")

    # 2. Try APIFY (cloud scraper)
    apify_key = os.getenv("APIFY_API_KEY")
    if apify_key:
        result = await fetch_via_apify(video_id, apify_key)
        if result:
            return result
        errors.append("APIFY: No transcript returned")
    else:
        errors.append("APIFY: API key not configured")

    # 3. Try Supadata (API service)
    supadata_key = os.getenv("SUPADATA_API_KEY")
    if supadata_key:
        result = await fetch_via_supadata(video_id, supadata_key)
        if result:
            return result
        errors.append("Supadata: No transcript available")
    else:
        errors.append("Supadata: API key not configured")

    # All services failed
    raise TranscriptNotFoundError(
        f"Could not fetch transcript for {video_id}. Tried: {'; '.join(errors)}"
    )


# === OUTPUT FORMATTING ===

def format_plain_text(result: TranscriptResult) -> str:
    """Format as plain text."""
    return result.text


def format_with_timestamps(result: TranscriptResult) -> str:
    """Format with timestamps."""
    if not result.segments:
        return result.text

    lines = []
    for seg in result.segments:
        start = seg.get("start", 0)
        minutes = int(start // 60)
        seconds = int(start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {seg.get('text', '')}")
    return '\n'.join(lines)


def format_json(result: TranscriptResult) -> str:
    """Format as JSON."""
    return json.dumps(asdict(result), indent=2, ensure_ascii=False)


# === MAIN ===

async def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcript with waterfall fallback"
    )
    parser.add_argument("url", help="YouTube video URL or ID")
    parser.add_argument("--timestamps", action="store_true", help="Include timestamps")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show which service was used")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    VERBOSE = args.verbose

    # Load environment variables
    load_env_file()

    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from '{args.url}'", file=sys.stderr)
        sys.exit(1)

    log(f"Video ID: {video_id}")

    try:
        result = await fetch_transcript_waterfall(video_id)

        if args.json:
            print(format_json(result))
        elif args.timestamps:
            print(format_with_timestamps(result))
        else:
            print(format_plain_text(result))

    except TranscriptNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
