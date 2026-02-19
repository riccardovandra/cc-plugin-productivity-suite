#!/usr/bin/env python3
"""
Import CSV file into Google Sheets.

Usage:
    python csv_import.py --file "data.csv" --title "Imported Data"
    python csv_import.py --file "leads.csv" --title "Leads" --folder "Client Work"
    python csv_import.py --file "data.csv" --id "EXISTING_SPREADSHEET_ID" --sheet "NewSheet"
    python csv_import.py --file "data.csv" --title "Data" --headers
"""

import argparse
import csv
import sys
from pathlib import Path
from sheets_client import GoogleSheetsClient, extract_id


def read_csv(file_path: str) -> list[list[str]]:
    """Read CSV file and return as 2D list."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    return rows


def main():
    parser = argparse.ArgumentParser(
        description='Import CSV file into Google Sheets'
    )
    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Path to CSV file'
    )
    parser.add_argument(
        '--title', '-t',
        help='Create new spreadsheet with this title'
    )
    parser.add_argument(
        '--id', '-i',
        help='Existing spreadsheet ID or URL (append to it)'
    )
    parser.add_argument(
        '--sheet', '-s',
        default='Sheet1',
        help='Target sheet name (default: Sheet1)'
    )
    parser.add_argument(
        '--folder',
        help='Google Drive folder path (for new spreadsheets)'
    )
    parser.add_argument(
        '--headers',
        action='store_true',
        help='Format first row as headers (bold, blue background, frozen)'
    )

    args = parser.parse_args()

    # Validate: need either --title (new) or --id (existing)
    if not args.title and not args.id:
        print("Error: Provide --title (new spreadsheet) or --id (existing)", file=sys.stderr)
        sys.exit(1)

    if args.title and args.id:
        print("Error: Use either --title or --id, not both", file=sys.stderr)
        sys.exit(1)

    # Read CSV
    rows = read_csv(args.file)
    if not rows:
        print("Error: CSV file is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Read {len(rows)} rows from CSV")

    client = GoogleSheetsClient()

    # Create new spreadsheet
    if args.title:
        folder_id = None
        if args.folder:
            folder_id = client.get_folder_id(args.folder)
            if not folder_id:
                print(f"Warning: Folder '{args.folder}' not found, creating in root")

        # Create with headers if requested
        if args.headers and rows:
            result = client.create_spreadsheet(
                title=args.title,
                headers=rows[0],
                sheet_title=args.sheet,
                folder_id=folder_id
            )
            # Write remaining data (skip header row)
            if len(rows) > 1:
                client.append_rows(
                    spreadsheet_id=result['id'],
                    sheet_title=args.sheet,
                    values=rows[1:]
                )
        else:
            result = client.create_spreadsheet(
                title=args.title,
                sheet_title=args.sheet,
                folder_id=folder_id
            )
            # Write all data
            client.write_range(
                spreadsheet_id=result['id'],
                range_notation=f"'{args.sheet}'!A1",
                values=rows
            )

        print(f"Created: {result['title']}")
        print(result['url'])

    # Append to existing spreadsheet
    else:
        spreadsheet_id = extract_id(args.id)

        # Check if we need to create a new sheet
        existing_sheets = client.list_sheets(spreadsheet_id)
        sheet_exists = any(s['title'] == args.sheet for s in existing_sheets)

        if not sheet_exists:
            client.add_sheet(spreadsheet_id, args.sheet)
            print(f"Created new sheet '{args.sheet}'")

        # Write data
        if args.headers and rows:
            client.set_headers(spreadsheet_id, rows[0], args.sheet)
            if len(rows) > 1:
                client.append_rows(
                    spreadsheet_id=spreadsheet_id,
                    sheet_title=args.sheet,
                    values=rows[1:]
                )
        else:
            client.write_range(
                spreadsheet_id=spreadsheet_id,
                range_notation=f"'{args.sheet}'!A1",
                values=rows
            )

        print(f"Imported {len(rows)} rows to '{args.sheet}'")
        print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


if __name__ == '__main__':
    main()
