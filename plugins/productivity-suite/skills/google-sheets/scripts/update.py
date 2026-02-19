#!/usr/bin/env python3
"""
Update specific cells or ranges in a Google Spreadsheet.

Usage:
    python update.py --id "SPREADSHEET_ID" --range "A1" --value "Hello"
    python update.py --id "SPREADSHEET_ID" --range "A1:C1" --data "Val1,Val2,Val3"
    python update.py --id "SPREADSHEET_ID" --range "A1:B2" --json '[["A","B"],["C","D"]]'
"""

import argparse
import json
import sys
from sheets_client import GoogleSheetsClient, extract_id


def main():
    parser = argparse.ArgumentParser(
        description='Update cells in a Google Spreadsheet'
    )
    parser.add_argument(
        '--id', '-i',
        required=True,
        help='Spreadsheet ID or URL'
    )
    parser.add_argument(
        '--range', '-r',
        required=True,
        help='A1 notation range (e.g., "A1", "Sheet1!A1:C3")'
    )
    parser.add_argument(
        '--value', '-v',
        help='Single cell value'
    )
    parser.add_argument(
        '--data', '-d',
        help='Comma-separated values for a single row'
    )
    parser.add_argument(
        '--json', '-j',
        help='JSON 2D array: [["A","B"],["C","D"]]'
    )
    parser.add_argument(
        '--raw',
        action='store_true',
        help='Use RAW input (no formula parsing)'
    )

    args = parser.parse_args()

    # Validate input
    if not args.value and not args.data and not args.json:
        print("Error: Provide --value, --data, or --json", file=sys.stderr)
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
    elif args.data:
        values = [args.data.split(',')]
    else:
        values = [[args.value]]

    # Extract spreadsheet ID
    spreadsheet_id = extract_id(args.id)

    # Determine value input option
    value_input_option = 'RAW' if args.raw else 'USER_ENTERED'

    # Update range
    client = GoogleSheetsClient()
    success = client.write_range(
        spreadsheet_id=spreadsheet_id,
        range_notation=args.range,
        values=values,
        value_input_option=value_input_option
    )

    if success:
        print(f"Updated range '{args.range}'")
        print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    else:
        print("Failed to update range", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
