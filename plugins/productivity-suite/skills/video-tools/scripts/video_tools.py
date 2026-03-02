#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.1.0",
#     "ffmpeg-python>=0.2.0",
# ]
# ///
"""
Video Tools - FFmpeg utilities for video file manipulation.

Provides format conversion and audio extraction. No transcription or AI.

Usage:
    uv run video_tools.py extract-audio video.mp4 audio.wav
    uv run video_tools.py to-mp4 input.avi output.mp4
    uv run video_tools.py to-webm input.mp4 output.webm
"""

import subprocess
from pathlib import Path

import click
import ffmpeg


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


def validate_input_file(file_path: str) -> Path:
    """Validate that the input file exists."""
    path = Path(file_path)
    if not path.exists():
        raise click.ClickException(f"Input file does not exist: {file_path}")
    if not path.is_file():
        raise click.ClickException(f"Input path is not a file: {file_path}")
    return path


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Video Tools - FFmpeg utilities for video file manipulation.

    Convert formats and extract audio from video files.
    """
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--format",
    default="wav",
    type=click.Choice(["wav", "mp3", "aac", "flac"], case_sensitive=False),
    help="Output audio format (default: wav)"
)
def extract_audio(input_file: str, output_file: str, format: str):
    """
    Extract audio from a video file.

    \b
    Examples:
        video_tools.py extract-audio video.mp4 audio.wav
        video_tools.py extract-audio video.mp4 audio.mp3 --format mp3
    """
    if not check_ffmpeg():
        raise click.ClickException(
            "FFmpeg is not installed. Please install it:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: apt-get install ffmpeg"
        )

    input_path = validate_input_file(input_file)
    output_path = Path(output_file)

    if not output_path.suffix:
        output_path = output_path.with_suffix(f".{format}")

    click.echo(f"Extracting audio from {input_path}...")
    click.echo(f"Output format: {format}")

    try:
        stream = ffmpeg.input(str(input_path))
        stream = ffmpeg.output(stream, str(output_path), acodec="pcm_s16le" if format == "wav" else format, vn=None)
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        click.echo(f"Audio extracted successfully to {output_path}")
        click.echo(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise click.ClickException(f"FFmpeg error during audio extraction:\n{error_msg}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option("--codec", default="libx264", help="Video codec (default: libx264)")
@click.option(
    "--preset",
    default="medium",
    type=click.Choice(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], case_sensitive=False),
    help="Encoding preset (default: medium)"
)
@click.option("--crf", default=23, type=int, help="Quality factor (default: 23, lower=better, range: 0-51)")
def to_mp4(input_file: str, output_file: str, codec: str, preset: str, crf: int):
    """
    Convert a video file to MP4 format.

    \b
    Examples:
        video_tools.py to-mp4 input.avi output.mp4
        video_tools.py to-mp4 input.mov output.mp4 --preset fast --crf 20
    """
    if not check_ffmpeg():
        raise click.ClickException(
            "FFmpeg is not installed. Please install it:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: apt-get install ffmpeg"
        )

    input_path = validate_input_file(input_file)
    output_path = Path(output_file)

    if output_path.suffix.lower() != ".mp4":
        output_path = output_path.with_suffix(".mp4")

    click.echo(f"Converting {input_path} to MP4...")
    click.echo(f"Codec: {codec}, Preset: {preset}, CRF: {crf}")

    try:
        stream = ffmpeg.input(str(input_path))
        stream = ffmpeg.output(
            stream, str(output_path),
            vcodec=codec, preset=preset, crf=crf,
            acodec="aac", audio_bitrate="128k"
        )
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        click.echo(f"Video converted successfully to {output_path}")
        click.echo(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise click.ClickException(f"FFmpeg error during MP4 conversion:\n{error_msg}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--codec",
    default="libvpx-vp9",
    type=click.Choice(["libvpx", "libvpx-vp9"], case_sensitive=False),
    help="Video codec (default: libvpx-vp9)"
)
@click.option("--crf", default=30, type=int, help="Quality factor (default: 30, lower=better, range: 0-63)")
@click.option("--bitrate", default="1M", help="Target bitrate (default: 1M)")
def to_webm(input_file: str, output_file: str, codec: str, crf: int, bitrate: str):
    """
    Convert a video file to WebM format (web-optimized).

    \b
    Examples:
        video_tools.py to-webm input.mp4 output.webm
        video_tools.py to-webm input.avi output.webm --codec libvpx-vp9 --crf 25
    """
    if not check_ffmpeg():
        raise click.ClickException(
            "FFmpeg is not installed. Please install it:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: apt-get install ffmpeg"
        )

    input_path = validate_input_file(input_file)
    output_path = Path(output_file)

    if output_path.suffix.lower() != ".webm":
        output_path = output_path.with_suffix(".webm")

    click.echo(f"Converting {input_path} to WebM...")
    click.echo(f"Codec: {codec}, CRF: {crf}, Bitrate: {bitrate}")

    try:
        stream = ffmpeg.input(str(input_path))
        stream = ffmpeg.output(
            stream, str(output_path),
            vcodec=codec, crf=crf,
            acodec="libopus", audio_bitrate="128k",
            **{"b:v": bitrate}
        )
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        click.echo(f"Video converted successfully to {output_path}")
        click.echo(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise click.ClickException(f"FFmpeg error during WebM conversion:\n{error_msg}")


if __name__ == "__main__":
    cli()
