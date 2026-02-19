#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client>=2.100.0",
#     "google-auth-oauthlib>=1.1.0",
#     "google-auth>=2.23.0",
# ]
# ///
"""
Upload a large file to Google Drive with resumable upload and progress tracking.

Usage:
    uv run upload_large.py --file video.mp4
    uv run upload_large.py --file large_archive.zip --folder-id <folder_id> --chunksize 5242880
"""

import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR.parent / 'modules'
sys.path.insert(0, str(MODULES_DIR))

from drive_client import DriveClient


def progress_bar(progress: int, width: int = 40) -> str:
    """Generate a simple progress bar."""
    filled = int(width * progress / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"\r[{bar}] {progress}%"


def main():
    parser = argparse.ArgumentParser(
        description='Upload a large file to Google Drive with progress tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload large video
  uv run upload_large.py --file video.mp4

  # Upload to specific folder with larger chunks
  uv run upload_large.py --file archive.zip --folder-id <folder_id> --chunksize 5242880

  # Upload with custom name
  uv run upload_large.py --file footage.mp4 --name "Conference Talk 2024.mp4"

Notes:
  - Chunksize is in bytes (default: 1MB = 1048576)
  - For very large files (1GB+), use 5MB+ chunks for better performance
  - Upload is resumable - interrupted uploads can be resumed (future feature)
        """
    )
    parser.add_argument('--file', '-f', required=True,
                        help='Path to file to upload')
    parser.add_argument('--name', '-n',
                        help='Custom filename (defaults to original name)')
    parser.add_argument('--folder-id', '-F',
                        help='Parent folder ID (defaults to root)')
    parser.add_argument('--profile', '-p', default='default',
                        choices=['default', 'youtube'],
                        help='Account profile (default: default)')
    parser.add_argument('--chunksize', '-c', type=int, default=1024 * 1024,
                        help='Upload chunk size in bytes (default: 1MB)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')

    args = parser.parse_args()

    # Validate file
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    file_size = file_path.stat().st_size
    size_mb = file_size / 1024 / 1024

    print(f"File: {file_path.name}", file=sys.stderr)
    print(f"Size: {size_mb:.1f} MB ({file_size:,} bytes)", file=sys.stderr)
    print(f"Profile: {args.profile}", file=sys.stderr)
    print(f"Chunk size: {args.chunksize / 1024:.0f} KB", file=sys.stderr)
    print(file=sys.stderr)

    try:
        client = DriveClient(profile=args.profile, readonly=False)

        last_progress = -1

        def progress_callback(progress: int):
            nonlocal last_progress
            if not args.quiet and progress != last_progress:
                print(progress_bar(progress), end='', file=sys.stderr, flush=True)
                last_progress = progress

        result = client.upload_large(
            file_path=str(file_path),
            name=args.name,
            folder_id=args.folder_id,
            chunksize=args.chunksize,
            progress_callback=progress_callback
        )

        if not args.quiet:
            print()  # New line after progress bar

        print("Upload successful!", file=sys.stderr)
        print(f"Name: {result.get('name')}")
        print(f"ID: {result.get('id')}")
        print(f"View: {result.get('webViewLink')}")
        if result.get('md5Checksum'):
            print(f"MD5: {result.get('md5Checksum')}")
        if result.get('size'):
            print(f"Size: {int(result['size']) / 1024 / 1024:.1f} MB")

    except KeyboardInterrupt:
        print("\nUpload interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
