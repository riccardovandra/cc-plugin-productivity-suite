#!/usr/bin/env python3
"""
Append rows to an existing Google Spreadsheet.

Usage:
    python append.py --id "SPREADSHEET_ID" --data "Value1,Value2,Value3"
    python append.py --id "SPREADSHEET_ID" --sheet "Sheet2" --data "A,B,C"
    python append.py --id "SPREADSHEET_ID" --json '[["Row1A","Row1B"],["Row2A","Row2B"]]'
"""

import argparse
import json
import sys
from sheets_client import GoogleSheetsClient, extract_id


def main():
    parser = argparse.ArgumentParser(
        description='Append rows to a Google Spreadsheet'
    )
    parser.add_argument(
        '--id', '-i',
        required=True,
        help='Spreadsheet ID or URL'
    )
    parser.add_argument(
        '--sheet', '-s',
        default='Sheet1',
        help='Target sheet name (default: Sheet1)'
    )
    parser.add_argument(
        '--data', '-d',
        help='Comma-separated values for a single row'
    )
    parser.add_argument(
        '--json', '-j',
        help='JSON array for multiple rows: [["A","B"],["C","D"]]'
    )

    args = parser.parse_args()

    # Validate input
    if not args.data and not args.json:
        print("Error: Provide either --data or --json", file=sys.stderr)
        sys.exit(1)

    # Parse data
    if args.json:
        try:
            values = json.loads(args.json)
            # Ensure it's a 2D array
            if values and not isinstance(values[0], list):
                values = [values]
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Single row from comma-separated values
        values = [args.data.split(',')]

    # Extract spreadsheet ID
    spreadsheet_id = extract_id(args.id)

    # Append rows
    client = GoogleSheetsClient()
    success = client.append_rows(
        spreadsheet_id=spreadsheet_id,
        sheet_title=args.sheet,
        values=values
    )

    if success:
        row_count = len(values)
        print(f"Appended {row_count} row{'s' if row_count > 1 else ''} to '{args.sheet}'")
        print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    else:
        print("Failed to append rows", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
