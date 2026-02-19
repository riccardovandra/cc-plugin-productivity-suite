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
List contents of a Google Drive folder.

Usage:
    uv run list.py
    uv run list.py --folder-id <folder_id> --profile youtube
    uv run list.py --format json
"""

import sys
import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR.parent / 'modules'
sys.path.insert(0, str(MODULES_DIR))

from drive_client import DriveClient


def format_item(item: dict, format: str = 'table') -> str:
    """Format folder item for output."""
    if format == 'json':
        return json.dumps(item, indent=2)

    icon = '📁' if item.get('mimeType') == 'application/vnd.google-apps.folder' else '📄'
    size = item.get('size')
    size_str = f" ({int(size) / 1024 / 1024:.1f} MB)" if size else ""

    return f"{icon} {item.get('name')}{size_str} [{item.get('id')}]"


def main():
    parser = argparse.ArgumentParser(
        description='List contents of a Google Drive folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List root folder
  uv run list.py

  # List specific folder
  uv run list.py --folder-id 1AbCdEfGhIjKlMnOpQrStUvWxYz

  # List in personal account
  uv run list.py --profile youtube

  # JSON output
  uv run list.py --format json
        """
    )
    parser.add_argument('--folder-id', '-f', default='root',
                        help='Folder ID to list (default: root)')
    parser.add_argument('--profile', '-p', default='default',
                        choices=['default', 'youtube'],
                        help='Account profile (default: default)')
    parser.add_argument('--format', '-F', default='table',
                        choices=['table', 'json', 'compact'],
                        help='Output format (default: table)')

    args = parser.parse_args()

    try:
        client = DriveClient(profile=args.profile, readonly=True)
        print(f"Listing folder: {args.folder_id} (profile: {args.profile})", file=sys.stderr)

        items = client.list_folder(args.folder_id)

        print(f"Found {len(items)} items:\n", file=sys.stderr)

        if args.format == 'json':
            print(json.dumps(items, indent=2))
        elif args.format == 'compact':
            for item in items:
                print(f"{item.get('mimeType') == 'application/vnd.google-apps.folder' and 'FOLDER' or 'FILE'} | {item.get('id')} | {item.get('name')}")
        else:  # table
            folders = [i for i in items if i.get('mimeType') == 'application/vnd.google-apps.folder']
            files = [i for i in items if i.get('mimeType') != 'application/vnd.google-apps.folder']

            if folders:
                print("Folders:")
                for item in folders:
                    print(f"  {format_item(item, args.format)}")

            if files:
                if folders:
                    print()
                print("Files:")
                for item in files:
                    print(f"  {format_item(item, args.format)}")

            if not items:
                print("  (empty folder)")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
