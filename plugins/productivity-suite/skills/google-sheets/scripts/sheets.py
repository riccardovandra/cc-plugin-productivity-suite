#!/usr/bin/env python3
"""
Manage sheets within a Google Spreadsheet.

Usage:
    python sheets.py --id "SPREADSHEET_ID" --list
    python sheets.py --id "SPREADSHEET_ID" --add "NewSheet"
    python sheets.py --id "SPREADSHEET_ID" --duplicate "Template" --as "January"
    python sheets.py --id "SPREADSHEET_ID" --delete "OldSheet"
    python sheets.py --id "SPREADSHEET_ID" --rename "OldName" --as "NewName"
"""

import argparse
import sys
from sheets_client import GoogleSheetsClient, extract_id


def main():
    parser = argparse.ArgumentParser(
        description='Manage sheets in a Google Spreadsheet'
    )
    parser.add_argument(
        '--id', '-i',
        required=True,
        help='Spreadsheet ID or URL'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all sheets'
    )
    parser.add_argument(
        '--add', '-a',
        metavar='NAME',
        help='Add a new blank sheet'
    )
    parser.add_argument(
        '--duplicate', '-d',
        metavar='SOURCE',
        help='Source sheet to duplicate'
    )
    parser.add_argument(
        '--rename',
        metavar='OLD_NAME',
        help='Sheet to rename'
    )
    parser.add_argument(
        '--as',
        dest='new_name',
        metavar='NEW_NAME',
        help='New name for duplicated or renamed sheet'
    )
    parser.add_argument(
        '--delete',
        metavar='NAME',
        help='Sheet to delete'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation for delete'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.duplicate and not args.new_name:
        print("Error: --duplicate requires --as NEW_NAME", file=sys.stderr)
        sys.exit(1)

    if args.rename and not args.new_name:
        print("Error: --rename requires --as NEW_NAME", file=sys.stderr)
        sys.exit(1)

    # Extract spreadsheet ID
    spreadsheet_id = extract_id(args.id)
    client = GoogleSheetsClient()

    # List sheets
    if args.list:
        sheets = client.list_sheets(spreadsheet_id)
        if sheets:
            print(f"Sheets in spreadsheet ({len(sheets)}):")
            for sheet in sheets:
                print(f"  {sheet['index']}. {sheet['title']}")
        else:
            print("No sheets found or error occurred")
        return

    # Add new sheet
    if args.add:
        sheet_id = client.add_sheet(spreadsheet_id, args.add)
        if sheet_id is not None:
            print(f"Created sheet '{args.add}'")
            print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}")
        else:
            print(f"Failed to create sheet '{args.add}'", file=sys.stderr)
            sys.exit(1)
        return

    # Duplicate sheet
    if args.duplicate:
        sheet_id = client.duplicate_sheet(
            spreadsheet_id,
            args.duplicate,
            args.new_name
        )
        if sheet_id is not None:
            print(f"Duplicated '{args.duplicate}' as '{args.new_name}'")
            print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}")
        else:
            print(f"Failed to duplicate sheet", file=sys.stderr)
            sys.exit(1)
        return

    # Rename sheet
    if args.rename:
        success = client.rename_sheet(spreadsheet_id, args.rename, args.new_name)
        if success:
            print(f"Renamed '{args.rename}' to '{args.new_name}'")
        else:
            print(f"Failed to rename sheet", file=sys.stderr)
            sys.exit(1)
        return

    # Delete sheet
    if args.delete:
        if not args.force:
            confirm = input(f"Delete sheet '{args.delete}'? (y/N): ")
            if confirm.lower() != 'y':
                print("Cancelled")
                return

        success = client.delete_sheet(spreadsheet_id, args.delete)
        if success:
            print(f"Deleted sheet '{args.delete}'")
        else:
            print(f"Failed to delete sheet", file=sys.stderr)
            sys.exit(1)
        return

    # No action specified
    print("No action specified. Use --list, --add, --duplicate, --rename, or --delete")
    parser.print_help()


if __name__ == '__main__':
    main()
