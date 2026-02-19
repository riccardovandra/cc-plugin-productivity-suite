#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
Fetch all transcripts from a YouTube channel.

Lists all videos from a channel and fetches transcripts for each.
Uses yt-dlp for video listing and the existing waterfall for transcripts.

Usage:
    # Fetch all transcripts from a channel
    uv run fetch_channel.py https://www.youtube.com/@jacobdietle

    # Limit to most recent N videos
    uv run fetch_channel.py https://www.youtube.com/@channelname --limit 10

    # Save to specific output directory
    uv run fetch_channel.py https://www.youtube.com/@channelname --output ./transcripts

    # Include timestamps in transcripts
    uv run fetch_channel.py https://www.youtube.com/@channelname --timestamps

    # Skip videos that already have transcripts saved
    uv run fetch_channel.py https://www.youtube.com/@channelname --skip-existing
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Import from the main transcript script
from youtube_transcript import (
    fetch_transcript_waterfall,
    format_plain_text,
    format_with_timestamps,
    format_json,
    load_env_file,
    TranscriptNotFoundError,
)


def slugify(text: str) -> str:
    """Convert text to a safe filename."""
    # Remove special characters, keep alphanumeric and spaces
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    # Limit length
    return text[:80]


def get_channel_videos(channel_url: str, limit: int = None) -> list[dict]:
    """
    Fetch list of all videos from a YouTube channel using yt-dlp.

    Returns list of dicts with: video_id, title, upload_date, duration, url
    """
    print(f"Fetching video list from: {channel_url}", file=sys.stderr)

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        channel_url
    ]

    if limit:
        cmd.extend(["--playlist-end", str(limit)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout for large channels
        )

        if result.returncode != 0:
            print(f"Error: yt-dlp failed: {result.stderr[:500]}", file=sys.stderr)
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                videos.append({
                    "video_id": data.get("id"),
                    "title": data.get("title", "Untitled"),
                    "upload_date": data.get("upload_date"),
                    "duration": data.get("duration"),
                    "url": f"https://www.youtube.com/watch?v={data.get('id')}"
                })
            except json.JSONDecodeError:
                continue

        print(f"Found {len(videos)} videos", file=sys.stderr)
        return videos

    except subprocess.TimeoutExpired:
        print("Error: Timeout fetching video list", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Error: yt-dlp not installed. Run: brew install yt-dlp", file=sys.stderr)
        return []


async def fetch_and_save_transcript(
    video: dict,
    output_dir: Path,
    timestamps: bool = False,
    skip_existing: bool = False
) -> tuple[bool, str]:
    """
    Fetch transcript for a video and save to output directory.

    Returns (success, message)
    """
    video_id = video["video_id"]
    title = video["title"]
    safe_title = slugify(title)

    # Build filename
    filename = f"{safe_title}_{video_id}.txt"
    output_path = output_dir / filename

    # Skip if already exists
    if skip_existing and output_path.exists():
        return (True, f"Skipped (exists): {title[:50]}")

    try:
        result = await fetch_transcript_waterfall(video_id)

        # Format transcript
        if timestamps:
            content = format_with_timestamps(result)
        else:
            content = format_plain_text(result)

        # Add metadata header
        header = f"# {title}\n"
        header += f"# Video ID: {video_id}\n"
        header += f"# URL: {video['url']}\n"
        if video.get("upload_date"):
            header += f"# Upload Date: {video['upload_date']}\n"
        header += f"# Source: {result.source}\n"
        header += f"# Fetched: {datetime.now().isoformat()}\n"
        header += "#" + "=" * 60 + "\n\n"

        # Save to file
        output_path.write_text(header + content, encoding="utf-8")

        return (True, f"Saved: {title[:50]}")

    except TranscriptNotFoundError as e:
        return (False, f"No transcript: {title[:50]}")
    except Exception as e:
        return (False, f"Error ({title[:30]}): {str(e)[:50]}")


async def fetch_channel_transcripts(
    channel_url: str,
    output_dir: Path,
    limit: int = None,
    timestamps: bool = False,
    skip_existing: bool = False,
    concurrency: int = 3
) -> dict:
    """
    Fetch all transcripts from a channel.

    Returns summary dict with counts.
    """
    # Get video list
    videos = get_channel_videos(channel_url, limit)

    if not videos:
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process videos with limited concurrency
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(video, index):
        async with semaphore:
            print(f"[{index + 1}/{len(videos)}] Processing: {video['title'][:50]}...", file=sys.stderr)
            return await fetch_and_save_transcript(
                video, output_dir, timestamps, skip_existing
            )

    # Create tasks
    tasks = [
        process_with_semaphore(video, i)
        for i, video in enumerate(videos)
    ]

    # Execute all tasks
    results = await asyncio.gather(*tasks)

    # Count results
    success = sum(1 for ok, _ in results if ok)
    failed = sum(1 for ok, msg in results if not ok and "No transcript" in msg)
    errors = sum(1 for ok, msg in results if not ok and "Error" in msg)
    skipped = sum(1 for ok, msg in results if ok and "Skipped" in msg)

    # Print summary
    print("\n" + "=" * 60, file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total videos: {len(videos)}", file=sys.stderr)
    print(f"Transcripts saved: {success - skipped}", file=sys.stderr)
    print(f"Skipped (existing): {skipped}", file=sys.stderr)
    print(f"No transcript available: {failed}", file=sys.stderr)
    print(f"Errors: {errors}", file=sys.stderr)
    print(f"Output directory: {output_dir}", file=sys.stderr)

    # Save manifest
    manifest = {
        "channel_url": channel_url,
        "fetched_at": datetime.now().isoformat(),
        "total_videos": len(videos),
        "transcripts_saved": success - skipped,
        "skipped": skipped,
        "no_transcript": failed,
        "errors": errors,
        "videos": [
            {
                "video_id": v["video_id"],
                "title": v["title"],
                "status": "success" if r[0] else "failed",
                "message": r[1]
            }
            for v, r in zip(videos, results)
        ]
    }

    manifest_path = output_dir / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest saved: {manifest_path}", file=sys.stderr)

    return {
        "total": len(videos),
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "errors": errors
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch all transcripts from a YouTube channel"
    )
    parser.add_argument(
        "channel_url",
        help="YouTube channel URL (e.g., https://www.youtube.com/@channelname)"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit to most recent N videos"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory (default: ./transcripts/{channel-name})"
    )
    parser.add_argument(
        "--timestamps", "-t",
        action="store_true",
        help="Include timestamps in transcripts"
    )
    parser.add_argument(
        "--skip-existing", "-s",
        action="store_true",
        help="Skip videos that already have saved transcripts"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=3,
        help="Number of concurrent transcript fetches (default: 3)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_env_file()

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        # Extract channel name from URL
        match = re.search(r'@([^/\s]+)', args.channel_url)
        if match:
            channel_name = match.group(1)
        else:
            channel_name = "channel"
        # Default to workspace/docs/ with dated folder
        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = Path(f"./workspace/docs/{today} - {channel_name} Transcripts")

    # Run the fetch
    await fetch_channel_transcripts(
        channel_url=args.channel_url,
        output_dir=output_dir,
        limit=args.limit,
        timestamps=args.timestamps,
        skip_existing=args.skip_existing,
        concurrency=args.concurrency
    )


if __name__ == "__main__":
    asyncio.run(main())
