#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "python-dotenv>=1.0.0", "click>=8.0.0"]
# ///
"""
Analyze videos using Gemini's native video understanding.

Supports both local video files and YouTube URLs.
Automatically handles long videos with waterfall strategy:
- Default settings (up to ~1 hour)
- Low resolution (up to ~3 hours)
- Low resolution + 0.5 FPS (very long videos)

Usage:
    uv run analyze_video.py <video_path_or_url>
    uv run analyze_video.py https://www.youtube.com/watch?v=VIDEO_ID
    uv run analyze_video.py video.mp4 --mode process
    uv run analyze_video.py <video> -o analysis.md
    uv run analyze_video.py <video> --low-res --fps 0.5

Environment:
    GEMINI_API_KEY - Google AI Studio API key
"""

import re

import click
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

# Load .env from project root (works for both local dev and plugin installs)
load_dotenv(Path.cwd() / ".env")


def is_youtube_url(text: str) -> bool:
    """Check if the input is a YouTube URL."""
    youtube_patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(https?://)?(www\.)?youtu\.be/[\w-]+',
        r'(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
    ]
    return any(re.match(pattern, text) for pattern in youtube_patterns)


def normalize_youtube_url(url: str) -> str:
    """Ensure YouTube URL has https:// prefix."""
    if not url.startswith('http'):
        return f'https://{url}'
    return url


PROMPTS = {
    "summary": """Analyze this video and provide a comprehensive summary.

## Overview
Provide a 2-3 sentence summary of what this video is about.

## Key Moments
List the key moments in the video with timestamps in format [MM:SS]:
- [00:00] - Description of what happens
- [01:30] - Next key moment
(Continue for all significant moments)

## Main Topics Covered
Bullet list of the main topics or themes discussed/shown.

## Key Takeaways
What are the most important points a viewer should remember?

Be thorough but concise. Focus on what matters most.""",

    "process": """You are analyzing a screen recording of manual activities performed in a software system.

Your task is to extract a detailed step-by-step process document that could be used to:
1. Train someone to perform this task
2. Document the process for automation planning
3. Identify all the screens, fields, buttons, and data involved

Please provide:

## Process Overview
A brief summary of what this process accomplishes.

## Prerequisites
What needs to be in place before starting (logged in, data available, etc.)

## Step-by-Step Process
For each action observed:
- Step number
- Screen/module being used
- Specific action taken (click, type, select, etc.)
- What data is entered or selected (if visible)
- Any waits or confirmations needed

## Data Fields Involved
List all input fields, dropdowns, checkboxes observed.

## Decision Points
Any branching logic or conditional steps observed.

## Notes for Automation
Observations relevant to automating this process (API calls that might replace UI actions, potential error states, etc.)

Be thorough and precise. If you can read text on screen, include it. If timestamps are relevant, note them.""",

    "visual": """Analyze the visual elements in this video thoroughly.

## Scene Overview
Describe the overall setting and context of the video.

## People
- Number of people visible
- Descriptions (if relevant to understanding the video)
- Actions they perform

## Objects & Elements
List all significant objects, items, or visual elements shown:
- Physical objects
- Digital interfaces/screens
- Text visible on screen (transcribe important text)
- Graphics, logos, or branding

## UI Elements (if applicable)
If this shows software or digital interfaces:
- Application/website being used
- Buttons, menus, forms visible
- Navigation elements
- Data displayed

## Scene Changes
Note any significant changes in what's shown:
- [Timestamp] - Description of change

## Visual Quality Notes
Any observations about video quality, lighting, framing that affect analysis.

Be detailed and specific. Describe what you actually see."""
}


def is_token_limit_error(error: Exception) -> bool:
    """Check if the error is a token limit exceeded error."""
    error_str = str(error).lower()
    return "token" in error_str and ("exceed" in error_str or "limit" in error_str)


def build_video_part(
    video_source: str,
    is_youtube: bool,
    video_file,
    fps: float | None = None
) -> types.Part:
    """Build the video Part with optional video_metadata for FPS."""
    if is_youtube:
        youtube_url = normalize_youtube_url(video_source)
        if fps is not None:
            return types.Part(
                file_data=types.FileData(file_uri=youtube_url),
                video_metadata=types.VideoMetadata(fps=fps)
            )
        else:
            return types.Part(
                file_data=types.FileData(file_uri=youtube_url)
            )
    else:
        # For uploaded files, video_metadata with fps
        if fps is not None:
            return types.Part(
                file_data=types.FileData(
                    file_uri=video_file.uri,
                    mime_type=video_file.mime_type
                ),
                video_metadata=types.VideoMetadata(fps=fps)
            )
        else:
            return video_file


def try_generate_with_settings(
    client,
    model: str,
    video_part: types.Part,
    prompt: str,
    low_res: bool = False
):
    """Attempt to generate content with specified settings."""
    config = None
    if low_res:
        config = types.GenerateContentConfig(
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW
        )

    return client.models.generate_content(
        model=model,
        contents=[video_part, prompt],
        config=config
    )


@click.command()
@click.argument("video_source")
@click.option(
    "--mode", "-m",
    type=click.Choice(["summary", "process", "visual"]),
    default="summary",
    help="Analysis mode: summary (default), process, or visual"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (optional, defaults to stdout)"
)
@click.option(
    "--model",
    default="gemini-2.5-flash",
    help="Gemini model to use (default: gemini-2.5-flash)"
)
@click.option(
    "--low-res",
    is_flag=True,
    help="Start with low resolution (default: auto-detect via waterfall)"
)
@click.option(
    "--fps",
    type=float,
    default=None,
    help="Custom frame rate (e.g., 0.5 for long videos). Default: 1 FPS"
)
@click.option(
    "--no-waterfall",
    is_flag=True,
    help="Disable automatic retry with lower settings on token limit errors"
)
def analyze_video(video_source: str, mode: str, output: str, model: str, low_res: bool, fps: float, no_waterfall: bool):
    """
    Analyze a video using Gemini's native video understanding.

    VIDEO_SOURCE: Path to a local video file OR a YouTube URL.
    """
    # Configure API
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        click.echo("Error: GEMINI_API_KEY environment variable not set", err=True)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Determine if input is YouTube URL or local file
    is_youtube = is_youtube_url(video_source)
    video_file = None
    source_display = video_source

    if is_youtube:
        # YouTube URL - pass directly to Gemini
        youtube_url = normalize_youtube_url(video_source)
        click.echo(f"Using YouTube URL: {youtube_url}")
        video_content = types.Part(
            file_data=types.FileData(file_uri=youtube_url)
        )
        source_display = youtube_url
    else:
        # Local file - upload to Gemini
        video_path = Path(video_source)
        if not video_path.exists():
            click.echo(f"Error: File not found: {video_source}", err=True)
            sys.exit(1)

        click.echo(f"Uploading video: {video_source}")
        video_file = client.files.upload(file=video_source)
        click.echo(f"Upload complete. URI: {video_file.uri}")

        # Wait for processing
        while video_file.state.name == "PROCESSING":
            click.echo("Processing video...")
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            click.echo(f"Error: Video processing failed: {video_file.state.name}", err=True)
            sys.exit(1)

        click.echo("Video ready for analysis.")
        video_content = video_file
        source_display = video_path.name

    # Get prompt for selected mode
    prompt = PROMPTS[mode]

    # Define waterfall strategies: (low_res, fps, description)
    strategies = []

    if fps is not None:
        # User specified FPS - use that with their low_res setting
        strategies = [(low_res, fps, f"{'low-res' if low_res else 'default'} + {fps} FPS")]
    elif low_res:
        # User specified low-res but no FPS
        strategies = [
            (True, None, "low resolution"),
            (True, 0.5, "low resolution + 0.5 FPS"),
        ]
    else:
        # Default: try waterfall from default settings
        strategies = [
            (False, None, "default settings"),
            (True, None, "low resolution"),
            (True, 0.5, "low resolution + 0.5 FPS"),
        ]

    if no_waterfall:
        # Only try the first strategy
        strategies = strategies[:1]

    # Try each strategy in order
    result = None
    last_error = None

    for idx, (use_low_res, use_fps, strategy_desc) in enumerate(strategies):
        click.echo(f"Analyzing video (mode: {mode}) with {strategy_desc}...")

        # Build video part with current FPS setting
        video_part = build_video_part(video_source, is_youtube, video_file, use_fps)

        try:
            response = try_generate_with_settings(
                client=client,
                model=model,
                video_part=video_part,
                prompt=prompt,
                low_res=use_low_res
            )
            result = response.text
            if idx > 0:
                click.echo(f"Success with {strategy_desc}!")
            break  # Success, exit loop

        except ClientError as e:
            last_error = e
            if is_token_limit_error(e) and idx < len(strategies) - 1:
                click.echo(f"Token limit exceeded with {strategy_desc}, trying next strategy...")
                continue
            else:
                # Not a token error or no more strategies
                raise

    if result is None:
        click.echo(f"Error: All strategies failed. Last error: {last_error}", err=True)
        sys.exit(1)

    # Output result
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(f"# Video Analysis\n\n")
            f.write(f"**Source:** `{source_display}`\n")
            f.write(f"**Mode:** {mode}\n\n")
            f.write(result)

        click.echo(f"Output saved to: {output}")
    else:
        click.echo("\n" + "=" * 50)
        click.echo(result)

    # Cleanup - delete uploaded file from Gemini (only for local files)
    if video_file:
        client.files.delete(name=video_file.name)
        click.echo("Cleaned up uploaded video from Gemini.")


if __name__ == "__main__":
    analyze_video()
