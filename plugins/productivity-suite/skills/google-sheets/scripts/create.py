#!/usr/bin/env python3
"""
Create Google Spreadsheet

Creates a new Google Spreadsheet with optional headers and folder placement.

Usage:
    python create.py --title "My Tracker" --headers "Date,Task,Status"
    python create.py --title "Habit Tracker" --headers "Date,Training,Meditation" --folder "Tracking"
    python create.py --title "Data" --json '{"headers": ["A", "B", "C"]}'
"""

import argparse
import json
import sys
from pathlib import Path

from sheets_client import GoogleSheetsClient


def create_spreadsheet(
    title: str,
    headers: list[str] = None,
    folder: str = None,
    sheet_title: str = "Sheet1"
) -> dict:
    """
    Create a Google Spreadsheet.

    Args:
        title: Spreadsheet title
        headers: List of header column names
        folder: Folder path (supports nested paths like "Parent/Child")
        sheet_title: Name of the first sheet

    Returns:
        Dict with 'id', 'title', 'url'
    """
    client = GoogleSheetsClient()

    # Get folder ID if specified
    folder_id = None
    if folder:
        folder_id = client.get_folder_id(folder, create_if_missing=False)
        if folder_id:
            print(f"Using folder: {folder}")
        else:
            print(f"Warning: Folder not found: {folder}", file=sys.stderr)
            print("Spreadsheet will be created in root.", file=sys.stderr)

    # Create spreadsheet
    result = client.create_spreadsheet(
        title=title,
        headers=headers,
        sheet_title=sheet_title,
        folder_id=folder_id
    )

    print(f"Created: {result['title']}")
    print(f"URL: {result['url']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Create Google Spreadsheet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create.py --title "My Tracker"
  python create.py --title "Habits" --headers "Date,Training,Meditation,Reading"
  python create.py --title "Report" --folder "Work/Reports"
  python create.py --title "Data" --json '{"headers": ["Col A", "Col B"]}'
"""
    )

    parser.add_argument('--title', '-t', required=True, help='Spreadsheet title')
    parser.add_argument('--headers', '-H', help='Comma-separated header names')
    parser.add_argument('--folder', '-f', help='Google Drive folder path')
    parser.add_argument('--sheet', '-s', default='Sheet1', help='First sheet name')
    parser.add_argument('--json', '-j', help='JSON config with headers and other options')

    args = parser.parse_args()

    # Parse headers
    headers = None
    if args.json:
        config = json.loads(args.json)
        headers = config.get('headers')
    elif args.headers:
        headers = [h.strip() for h in args.headers.split(',')]

    result = create_spreadsheet(
        title=args.title,
        headers=headers,
        folder=args.folder,
        sheet_title=args.sheet
    )

    print(f"\nSpreadsheet ID: {result['id']}")


if __name__ == '__main__':
    main()
