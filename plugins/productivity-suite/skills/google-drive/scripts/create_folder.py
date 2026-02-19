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
Create a folder in Google Drive.

Usage:
    uv run create_folder.py --name "Client Deliverables"
    uv run create_folder.py --name "Projects" --parent-id <folder_id> --profile youtube
"""

import sys
import argparse

SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR.parent / 'modules'
sys.path.insert(0, str(MODULES_DIR))

from drive_client import DriveClient


def main():
    parser = argparse.ArgumentParser(
        description='Create a folder in Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create folder in root
  uv run create_folder.py --name "Client Deliverables"

  # Create folder inside another folder
  uv run create_folder.py --name "2024 Projects" --parent-id 1AbCdEfGhIjKlMnOpQrStUvWxYz

  # Create in personal account
  uv run create_folder.py --name "Personal Videos" --profile youtube
        """
    )
    parser.add_argument('--name', '-n', required=True,
                        help='Folder name')
    parser.add_argument('--parent-id', '-p',
                        help='Parent folder ID (defaults to root)')
    parser.add_argument('--profile', default='default',
                        choices=['default', 'youtube'],
                        help='Account profile (default: default)')
    parser.add_argument('--get-or-create', '-g', action='store_true',
                        help='Return existing folder if it already exists')

    args = parser.parse_args()

    try:
        client = DriveClient(profile=args.profile, readonly=False)
        print(f"Using Drive profile: {args.profile}", file=sys.stderr)

        if args.get_or_create:
            result = client.get_or_create_folder(args.name, args.parent_id)
            if result.get('created'):  # Would need to track this in client
                print(f"Folder created: {result.get('name')}", file=sys.stderr)
            else:
                print(f"Using existing folder: {result.get('name')}", file=sys.stderr)
        else:
            result = client.create_folder(args.name, args.parent_id)
            print(f"Folder created: {result.get('name')}", file=sys.stderr)

        print(f"ID: {result.get('id')}")
        print(f"View: {result.get('webViewLink')}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
