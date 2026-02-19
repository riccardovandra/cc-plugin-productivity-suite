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
Search for files in Google Drive.

Usage:
    uv run search.py --query "name contains 'invoice'"
    uv run search.py --query "mimeType='application/pdf'" --profile youtube
    uv run search.py --query "modifiedTime > '2024-01-01T00:00:00'" --format json
"""

import sys
import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR.parent / 'modules'
sys.path.insert(0, str(MODULES_DIR))

from drive_client import DriveClient


def format_file(file: dict, format: str = 'table') -> str:
    """Format file for output."""
    if format == 'json':
        return json.dumps(file, indent=2)

    size = file.get('size')
    size_str = f"{int(size) / 1024 / 1024:.1f} MB" if size else "N/A"

    return (
        f"\n{'=' * 60}\n"
        f"Name: {file.get('name')}\n"
        f"ID: {file.get('id')}\n"
        f"Type: {file.get('mimeType')}\n"
        f"Size: {size_str}\n"
        f"Modified: {file.get('modifiedTime')}\n"
        f"Link: {file.get('webViewLink')}\n"
    )


def main():
    parser = argparse.ArgumentParser(
        description='Search for files in Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search Query Examples:
  name contains 'report'              Files with 'report' in name
  name = 'exact_name.pdf'             Exact filename match
  mimeType contains 'pdf'             PDF files
  mimeType = 'application/vnd.google-apps.folder'  Folders only
  modifiedTime > '2024-01-01T00:00:00'  Modified after date
  modifiedTime > '2024-01-01' and modifiedTime < '2024-12-31'  Date range
  trashed = false                     Exclude trashed files
  'me' in owners                     Files you own
  sharedWithMe = true                 Files shared with you

Combine with 'and'/''or':
  name contains 'invoice' and mimeType contains 'pdf'

See: https://developers.google.com/drive/api/guides/search-files
        """
    )
    parser.add_argument('--query', '-q', required=True,
                        help='Drive search query (see examples below)')
    parser.add_argument('--profile', '-p', default='default',
                        choices=['default', 'youtube'],
                        help='Account profile (default: default)')
    parser.add_argument('--format', '-f', default='table',
                        choices=['table', 'json', 'compact'],
                        help='Output format (default: table)')
    parser.add_argument('--limit', '-l', type=int, default=50,
                        help='Max results (default: 50)')
    parser.add_argument('--fields', help='Custom fields to return')

    args = parser.parse_args()

    try:
        client = DriveClient(profile=args.profile, readonly=True)
        print(f"Searching in Drive profile: {args.profile}", file=sys.stderr)

        results = client.search(
            query=args.query,
            fields=args.fields,
            page_size=args.limit
        )

        print(f"Found {len(results)} results:\n", file=sys.stderr)

        if args.format == 'json':
            print(json.dumps(results, indent=2))
        elif args.format == 'compact':
            for file in results:
                print(f"{file.get('id')} | {file.get('name')}")
        else:  # table
            for file in results:
                print(format_file(file, args.format))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
