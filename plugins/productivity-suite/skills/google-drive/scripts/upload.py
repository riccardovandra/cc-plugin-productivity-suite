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
Upload a file to Google Drive.

Usage:
    uv run upload.py --file document.pdf
    uv run upload.py --file video.mp4 --folder-id <folder_id> --profile youtube
    uv run upload.py --file report.pdf --name "Q4 Report.pdf"
"""

import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR.parent / 'modules'
sys.path.insert(0, str(MODULES_DIR))

from drive_client import DriveClient


def main():
    parser = argparse.ArgumentParser(
        description='Upload a file to Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload to root folder
  uv run upload.py --file document.pdf

  # Upload with custom name
  uv run upload.py --file report.pdf --name "Q4 Report 2024.pdf"

  # Upload to specific folder
  uv run upload.py --file video.mp4 --folder-id 1AbCdEfGhIjKlMnOpQrStUvWxYz

  # Upload to personal account
  uv run upload.py --file photo.jpg --profile youtube

  # Find folder ID first
  uv run ../search.py --query "name contains 'My Folder'" --format compact
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
    parser.add_argument('--mime-type',
                        help='MIME type (auto-detected if not specified)')

    args = parser.parse_args()

    try:
        client = DriveClient(profile=args.profile, readonly=False)
        print(f"Using Drive profile: {args.profile}", file=sys.stderr)

        result = client.upload(
            file_path=args.file,
            name=args.name,
            folder_id=args.folder_id,
            mime_type=args.mime_type
        )

        print("Upload successful!", file=sys.stderr)
        print(f"Name: {result.get('name')}")
        print(f"ID: {result.get('id')}")
        print(f"View: {result.get('webViewLink')}")
        if result.get('md5Checksum'):
            print(f"MD5: {result.get('md5Checksum')}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
