#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "aiohttp>=3.9.0",
#     "httpx>=0.27.0",
#     "ffmpeg-python>=0.2.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
Video Transcript Extractor - Unified transcript extraction from any source.

Supports:
- YouTube URLs (waterfall: yt-dlp -> APIFY -> Supadata)
- Loom URLs (yt-dlp)
- Local video/audio files (Groq Whisper -> local Whisper fallback)

Usage:
    # YouTube/Loom
    python transcript.py https://youtube.com/watch?v=VIDEO_ID
    python transcript.py https://www.loom.com/share/abc123
    python transcript.py <url> --timestamps

    # Local files
    python transcript.py recording.mp4 --backend groq
    python transcript.py interview.mp4 --backend groq --language it --format srt
    python transcript.py lecture.mp4 --backend groq -o transcript.txt
"""

import argparse
import asyncio
import html
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# === CONFIGURATION ===

APIFY_ACTOR_ID = "karamelo~youtube-transcripts"
APIFY_API_BASE = "https://api.apify.com/v2"
SUPADATA_API_BASE = "https://api.supadata.ai/v1"

PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]

GROQ_MAX_FILE_SIZE_MB = 25
GROQ_CHUNK_DURATION_MINUTES = 20

VERBOSE = False

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".flac", ".m4a", ".ogg"}


# === DATA STRUCTURES ===

@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    video_id: str
    source: str  # "ytdlp" | "apify" | "supadata" | "groq" | "local-whisper"
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


def detect_platform(url_or_id: str) -> tuple[str, str]:
    """Detect platform and extract ID from URL.

    Returns:
        (platform, id) where platform is "youtube", "loom", or "local"
    """
    # Check if it's a local file first
    if Path(url_or_id).exists():
        return "local", url_or_id

    # Loom URLs
    loom_match = re.search(r'loom\.com/(?:share|embed)/([a-f0-9]+)', url_or_id)
    if loom_match:
        return "loom", loom_match.group(1)

    # YouTube URLs
    yt_patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in yt_patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return "youtube", match.group(1)

    return "unknown", url_or_id


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube video ID from URL or return as-is if already an ID."""
    platform, video_id = detect_platform(url_or_id)
    if platform == "youtube":
        return video_id
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


# =============================================================================
# URL TRANSCRIPT SERVICES (YouTube / Loom)
# =============================================================================

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

    # Remove progressive-reveal duplicates: when consecutive segments share
    # the same start time, keep only the last (most complete) one
    if segments:
        deduped = []
        for seg in segments:
            if deduped and abs(seg.start - deduped[-1].start) < 0.01:
                # Same timestamp - replace with longer version
                deduped[-1] = seg
            elif deduped and seg.text.startswith(deduped[-1].text):
                # Current text is a superset of previous - replace
                deduped[-1] = seg
            elif deduped and deduped[-1].text.startswith(seg.text):
                # Previous is already a superset - skip this one
                pass
            else:
                deduped.append(seg)
        segments = deduped

    full_text = ' '.join(seg.text for seg in segments)
    return full_text, segments


async def fetch_via_ytdlp(video_id: str, languages: list[str], platform: str = "youtube", direct_url: str = None) -> Optional[TranscriptResult]:
    """Fetch transcript using yt-dlp CLI. Works for YouTube and Loom."""
    if not check_ytdlp_available():
        log("yt-dlp not installed, skipping...")
        return None

    log(f"Attempting yt-dlp ({platform})...")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(id)s.%(ext)s")

        if direct_url:
            url = direct_url
        else:
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


# === URL WATERFALL ORCHESTRATION ===

async def fetch_transcript_waterfall(
    video_id: str,
    languages: list[str] = None,
    platform: str = "youtube",
    original_url: str = None
) -> TranscriptResult:
    """Try each service in sequence until one succeeds."""
    if languages is None:
        languages = PREFERRED_LANGUAGES

    errors = []

    # For Loom, only yt-dlp works (APIFY/Supadata are YouTube-specific)
    if platform == "loom":
        loom_url = original_url or f"https://www.loom.com/share/{video_id}"
        result = await fetch_via_ytdlp(video_id, languages, platform="loom", direct_url=loom_url)
        if result:
            return result
        raise TranscriptNotFoundError(
            f"Could not fetch Loom transcript for {video_id}. "
            "yt-dlp failed - the video may be private or have no captions."
        )

    # YouTube: full waterfall
    # 1. Try yt-dlp (free, local)
    result = await fetch_via_ytdlp(video_id, languages, platform="youtube")
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


# =============================================================================
# LOCAL FILE TRANSCRIPTION (Groq Whisper / Local Whisper)
# =============================================================================

def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_media_duration(file_path: str) -> Optional[float]:
    """Get the duration of a media file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path)
            ],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        pass
    return None


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def split_audio_into_chunks(audio_path: Path, chunk_duration_minutes: int = 20) -> list[Path]:
    """Split audio file into chunks of specified duration using ffmpeg.

    Returns list of temporary chunk file paths.
    """
    import ffmpeg

    duration = get_media_duration(str(audio_path))
    if not duration:
        print("Error: Could not determine audio duration", file=sys.stderr)
        sys.exit(1)

    chunk_duration_seconds = chunk_duration_minutes * 60
    num_chunks = math.ceil(duration / chunk_duration_seconds)

    if num_chunks == 1:
        return [audio_path]  # No need to split

    print(f"Splitting audio into {num_chunks} chunks ({chunk_duration_minutes} min each)...", file=sys.stderr)

    chunk_paths = []
    for i in range(num_chunks):
        start_time = i * chunk_duration_seconds

        # Create temp file for this chunk
        chunk_file = tempfile.NamedTemporaryFile(suffix=f"_chunk{i}.mp3", delete=False)
        chunk_file.close()
        chunk_path = Path(chunk_file.name)

        try:
            stream = ffmpeg.input(str(audio_path), ss=start_time, t=chunk_duration_seconds)
            stream = ffmpeg.output(stream, str(chunk_path), acodec="libmp3lame", ab="64k", ac=1, ar="16000")
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
            print(f"  Chunk {i+1}/{num_chunks}: {chunk_size_mb:.1f} MB", file=sys.stderr)
            chunk_paths.append(chunk_path)
        except ffmpeg.Error as e:
            # Clean up any created chunks
            for p in chunk_paths:
                if p.exists():
                    os.unlink(p)
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"Error: Failed to split audio: {error_msg}", file=sys.stderr)
            sys.exit(1)

    return chunk_paths


def transcribe_with_groq(
    audio_path: Path,
    language: Optional[str] = None,
    model: str = "whisper-large-v3-turbo"
) -> tuple[list[dict], dict]:
    """Transcribe audio using Groq API with auto-chunking for large files.

    Returns (segments, info).
    """
    import httpx

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print(
            "Error: GROQ_API_KEY environment variable not set.\n"
            "Get your free API key at: https://console.groq.com",
            file=sys.stderr
        )
        sys.exit(1)

    # Check file size and split if needed
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    total_duration = get_media_duration(str(audio_path))

    if file_size_mb > GROQ_MAX_FILE_SIZE_MB:
        print(f"File size ({file_size_mb:.1f} MB) exceeds Groq limit ({GROQ_MAX_FILE_SIZE_MB} MB)", file=sys.stderr)
        chunks = split_audio_into_chunks(audio_path, GROQ_CHUNK_DURATION_MINUTES)
        needs_cleanup = len(chunks) > 1 or chunks[0] != audio_path
    else:
        chunks = [audio_path]
        needs_cleanup = False

    all_segments = []
    detected_language = None
    time_offset = 0.0

    try:
        with httpx.Client(timeout=300.0) as client:
            for i, chunk_path in enumerate(chunks):
                if len(chunks) > 1:
                    print(f"Transcribing chunk {i+1}/{len(chunks)}...", file=sys.stderr)

                with open(chunk_path, "rb") as f:
                    files = {"file": (chunk_path.name, f, "audio/mpeg")}
                    data = {
                        "model": model,
                        "response_format": "verbose_json",
                        "timestamp_granularities[]": "segment",
                    }
                    if language:
                        data["language"] = language

                    start_time = time.time()
                    response = client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files=files,
                        data=data,
                    )

                if response.status_code != 200:
                    error_detail = response.json().get("error", {}).get("message", response.text)
                    print(f"Error: Groq API error: {error_detail}", file=sys.stderr)
                    sys.exit(1)

                result = response.json()
                elapsed = time.time() - start_time

                chunk_duration = get_media_duration(str(chunk_path)) or 0
                if chunk_duration > 0:
                    speed = chunk_duration / elapsed
                    print(f"  Processed {format_duration(chunk_duration)} in {elapsed:.1f}s ({speed:.0f}x real-time)", file=sys.stderr)

                if "segments" in result:
                    for seg in result["segments"]:
                        all_segments.append({
                            "start": seg.get("start", 0) + time_offset,
                            "end": seg.get("end", 0) + time_offset,
                            "text": seg.get("text", "").strip()
                        })
                elif "text" in result:
                    all_segments.append({
                        "start": time_offset,
                        "end": time_offset + chunk_duration,
                        "text": result["text"].strip()
                    })

                if detected_language is None:
                    detected_language = result.get("language", "unknown")

                time_offset += chunk_duration

    finally:
        if needs_cleanup:
            for chunk_path in chunks:
                if chunk_path.exists() and chunk_path != audio_path:
                    try:
                        os.unlink(chunk_path)
                    except Exception:
                        pass

    info = {
        "language": detected_language or "unknown",
        "language_probability": 1.0,
        "duration": total_duration,
    }

    return all_segments, info


def transcribe_with_local_whisper(
    audio_path: Path,
    language: Optional[str] = None,
    model: str = "base"
) -> tuple[list[dict], dict]:
    """Transcribe audio using local faster-whisper.

    Returns (segments, info).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "Error: faster-whisper is not installed.\n"
            "Install it with: pip install faster-whisper\n"
            "Or use --backend groq instead (recommended, ~100x faster).",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"Loading Whisper model '{model}'...", file=sys.stderr)
    whisper_model = WhisperModel(model, device="cpu", compute_type="int8")

    print("Transcribing...", file=sys.stderr)
    transcribe_kwargs = {}
    if language:
        transcribe_kwargs["language"] = language

    segments_gen, info = whisper_model.transcribe(str(audio_path), **transcribe_kwargs)

    all_segments = []
    for segment in segments_gen:
        all_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })

    info_dict = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
    }

    return all_segments, info_dict


def transcribe_local_file(
    file_path: str,
    backend: str = "groq",
    model: Optional[str] = None,
    language: Optional[str] = None,
    output_format: str = "txt",
    output_file: Optional[str] = None,
) -> TranscriptResult:
    """Transcribe a local video/audio file.

    Returns TranscriptResult.
    """
    import ffmpeg

    if not check_ffmpeg():
        print(
            "Error: FFmpeg is not installed. Install it with:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: apt-get install ffmpeg",
            file=sys.stderr
        )
        sys.exit(1)

    input_path = Path(file_path)

    # Determine if we need to extract audio first
    temp_audio = None
    audio_file = input_path

    if input_path.suffix.lower() in VIDEO_EXTENSIONS:
        print(f"Extracting audio from video...", file=sys.stderr)
        audio_ext = ".mp3" if backend == "groq" else ".wav"
        temp_audio = tempfile.NamedTemporaryFile(suffix=audio_ext, delete=False)
        temp_audio.close()
        audio_file = Path(temp_audio.name)

        try:
            stream = ffmpeg.input(str(input_path))
            if backend == "groq":
                stream = ffmpeg.output(stream, str(audio_file), acodec="libmp3lame", ab="64k", ac=1, ar="16000", vn=None)
            else:
                stream = ffmpeg.output(stream, str(audio_file), acodec="pcm_s16le", ac=1, ar="16000", vn=None)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            print(f"Audio extracted ({audio_file.stat().st_size / (1024*1024):.1f} MB)", file=sys.stderr)
        except ffmpeg.Error as e:
            if temp_audio:
                os.unlink(audio_file)
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"Error: FFmpeg audio extraction failed: {error_msg}", file=sys.stderr)
            sys.exit(1)
    elif input_path.suffix.lower() not in AUDIO_EXTENSIONS:
        print(
            f"Error: Unsupported file format: {input_path.suffix}\n"
            f"Supported video: {', '.join(VIDEO_EXTENSIONS)}\n"
            f"Supported audio: {', '.join(AUDIO_EXTENSIONS)}",
            file=sys.stderr
        )
        sys.exit(1)

    total_duration = get_media_duration(str(audio_file))
    if total_duration:
        print(f"Duration: {format_duration(total_duration)}", file=sys.stderr)

    try:
        transcribe_start = time.time()

        if backend == "groq":
            groq_model = model if model and model.startswith("whisper-") else "whisper-large-v3-turbo"
            print(f"Transcribing with Groq (model: {groq_model})...", file=sys.stderr)
            all_segments, info = transcribe_with_groq(audio_file, language, groq_model)
        else:
            local_model = model or "base"
            print(f"Transcribing with local Whisper (model: {local_model})...", file=sys.stderr)
            all_segments, info = transcribe_with_local_whisper(audio_file, language, local_model)

        total_time = time.time() - transcribe_start
        print(f"Transcription completed in {format_duration(total_time)}", file=sys.stderr)
        print(f"Detected language: {info['language']}", file=sys.stderr)

        # Format output
        full_text = " ".join(seg["text"] for seg in all_segments)

        if output_format == "txt":
            content = "\n".join(seg["text"] for seg in all_segments)
        elif output_format == "srt":
            lines = []
            for i, seg in enumerate(all_segments, 1):
                start_ts = format_timestamp_srt(seg["start"])
                end_ts = format_timestamp_srt(seg["end"])
                lines.append(f"{i}")
                lines.append(f"{start_ts} --> {end_ts}")
                lines.append(seg["text"])
                lines.append("")
            content = "\n".join(lines)
        elif output_format == "vtt":
            lines = ["WEBVTT", ""]
            for seg in all_segments:
                start_ts = format_timestamp_vtt(seg["start"])
                end_ts = format_timestamp_vtt(seg["end"])
                lines.append(f"{start_ts} --> {end_ts}")
                lines.append(seg["text"])
                lines.append("")
            content = "\n".join(lines)
        elif output_format == "json":
            content = json.dumps({
                "language": info["language"],
                "language_probability": info.get("language_probability", 1.0),
                "segments": all_segments
            }, indent=2, ensure_ascii=False)

        # Output
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"Saved to: {output_path}", file=sys.stderr)
        else:
            print(content)

        # Build segments in TranscriptResult format
        result_segments = [
            {"text": seg["text"], "start": seg["start"], "duration": seg.get("end", seg["start"]) - seg["start"]}
            for seg in all_segments
        ]

        source = "groq" if backend == "groq" else "local-whisper"

        return TranscriptResult(
            video_id=input_path.stem,
            source=source,
            language=info["language"],
            text=full_text,
            segments=result_segments
        )

    finally:
        if temp_audio and audio_file.exists():
            try:
                os.unlink(audio_file)
            except Exception:
                pass


# =============================================================================
# OUTPUT FORMATTING (for URL transcripts)
# =============================================================================

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


def format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# =============================================================================
# MAIN CLI
# =============================================================================

async def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Extract transcript from any video source (YouTube, Loom, or local file)"
    )
    parser.add_argument("source", help="YouTube/Loom URL, video ID, or local file path")

    # URL-specific options
    parser.add_argument("--timestamps", action="store_true", help="Include timestamps (URL transcripts)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (URL transcripts)")

    # Local file options
    parser.add_argument("--backend", choices=["groq", "local"], default="groq",
                        help="Transcription backend for local files (default: groq)")
    parser.add_argument("--model", default=None,
                        help="Whisper model. Groq: whisper-large-v3-turbo. Local: tiny/base/small/medium/large")
    parser.add_argument("--language", default=None,
                        help="Language code (en, it, es, fr, de, zh). Auto-detect if not specified.")
    parser.add_argument("--format", dest="output_format", choices=["txt", "srt", "vtt", "json"],
                        default="txt", help="Output format for local files (default: txt)")

    # Shared options
    parser.add_argument("--output", "-o", default=None, help="Save to file instead of stdout")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")

    args = parser.parse_args()
    VERBOSE = args.verbose

    # Load environment variables
    load_env_file()

    # Detect platform and route accordingly
    platform, identifier = detect_platform(args.source)

    if platform == "local":
        # Local file transcription
        transcribe_local_file(
            file_path=args.source,
            backend=args.backend,
            model=args.model,
            language=args.language,
            output_format=args.output_format,
            output_file=args.output,
        )
    elif platform in ("youtube", "loom"):
        # URL transcript extraction
        log(f"Platform: {platform}, ID: {identifier}")

        try:
            result = await fetch_transcript_waterfall(
                identifier,
                platform=platform,
                original_url=args.source
            )

            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if args.json:
                    content = format_json(result)
                elif args.timestamps:
                    content = format_with_timestamps(result)
                else:
                    content = format_plain_text(result)

                output_path.write_text(content, encoding="utf-8")
                print(f"Saved to: {args.output}", file=sys.stderr)
            else:
                if args.json:
                    print(format_json(result))
                elif args.timestamps:
                    print(format_with_timestamps(result))
                else:
                    print(format_plain_text(result))

        except TranscriptNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: Could not detect source type from '{args.source}'", file=sys.stderr)
        print("Provide a YouTube/Loom URL or a path to a local video/audio file.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
