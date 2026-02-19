#!/usr/bin/env python3
"""
Google Sheets API Client

Core API wrapper for Google Sheets operations.
Used by other scripts in this skill.

Usage:
    from sheets_client import GoogleSheetsClient

    client = GoogleSheetsClient()
    sheet = client.create_spreadsheet("My Tracker", headers=["Date", "Task", "Status"])
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from googleapiclient.discovery import build
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install google-api-python-client")
    sys.exit(1)

# Add integrations to path for shared auth
SKILL_DIR = Path(__file__).parent.parent
INTEGRATIONS_DIR = SKILL_DIR.parent.parent / 'integrations/google/scripts'
sys.path.insert(0, str(INTEGRATIONS_DIR))

from google_auth import get_sheets_credentials, get_credentials


def extract_id(id_or_url: str) -> str:
    """
    Extract spreadsheet ID from URL or return ID as-is.

    Args:
        id_or_url: Spreadsheet ID or full Google Sheets URL

    Returns:
        Spreadsheet ID

    Examples:
        extract_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        extract_id("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit")
    """
    import re
    # Match Google Sheets URL pattern
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', id_or_url)
    if match:
        return match.group(1)
    # Already an ID
    return id_or_url.strip()


class GoogleSheetsClient:
    """Google Sheets API client wrapper."""

    def __init__(self):
        """Initialize Google Sheets client with Sheets and Drive services."""
        # Get credentials with both sheets and drive access
        credentials = get_credentials(['spreadsheets', 'drive'])
        self.sheets_service = build('sheets', 'v4', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)

    # =========================================================================
    # Spreadsheet Operations
    # =========================================================================

    def create_spreadsheet(
        self,
        title: str,
        headers: list[str] = None,
        sheet_title: str = "Sheet1",
        folder_id: str = None
    ) -> dict:
        """
        Create a new Google Spreadsheet.

        Args:
            title: Spreadsheet title
            headers: Optional list of header column names
            sheet_title: Name of the first sheet (default: "Sheet1")
            folder_id: Optional folder ID to create spreadsheet in

        Returns:
            Dict with 'id', 'title', 'url'
        """
        # Create the spreadsheet
        spreadsheet = {
            'properties': {'title': title},
            'sheets': [{
                'properties': {
                    'title': sheet_title,
                    'gridProperties': {'frozenRowCount': 1} if headers else {}
                }
            }]
        }

        result = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = result['spreadsheetId']

        # Add headers if provided
        if headers:
            self.set_headers(spreadsheet_id, headers, sheet_title)

        # Move to folder if specified
        if folder_id:
            self._move_to_folder(spreadsheet_id, folder_id)

        return {
            'id': spreadsheet_id,
            'title': title,
            'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        }

    def set_headers(
        self,
        spreadsheet_id: str,
        headers: list[str],
        sheet_title: str = "Sheet1"
    ) -> bool:
        """
        Set header row with formatting.

        Args:
            spreadsheet_id: Spreadsheet ID
            headers: List of header names
            sheet_title: Sheet name

        Returns:
            True if successful
        """
        try:
            # Write headers
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A1",
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()

            # Get sheet ID for formatting
            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheet_id = 0
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == sheet_title:
                    sheet_id = sheet['properties']['sheetId']
                    break

            # Format headers (bold, blue background, white text, centered)
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                                'textFormat': {
                                    'bold': True,
                                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                                },
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                    }
                },
                # Auto-resize columns
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': len(headers)
                        }
                    }
                }
            ]

            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()

            return True

        except Exception as e:
            print(f"Error setting headers: {e}", file=sys.stderr)
            return False

    def get_spreadsheet(self, spreadsheet_id: str) -> Optional[dict]:
        """
        Get spreadsheet metadata.

        Args:
            spreadsheet_id: Spreadsheet ID

        Returns:
            Spreadsheet metadata or None
        """
        try:
            return self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
        except Exception as e:
            print(f"Error getting spreadsheet: {e}", file=sys.stderr)
            return None

    def read_range(
        self,
        spreadsheet_id: str,
        range_notation: str
    ) -> list[list]:
        """
        Read data from a range.

        Args:
            spreadsheet_id: Spreadsheet ID
            range_notation: A1 notation (e.g., "Sheet1!A1:D10")

        Returns:
            2D list of values
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_notation
            ).execute()
            return result.get('values', [])
        except Exception as e:
            print(f"Error reading range: {e}", file=sys.stderr)
            return []

    def write_range(
        self,
        spreadsheet_id: str,
        range_notation: str,
        values: list[list],
        value_input_option: str = 'USER_ENTERED'
    ) -> bool:
        """
        Write data to a range.

        Args:
            spreadsheet_id: Spreadsheet ID
            range_notation: A1 notation (e.g., "Sheet1!A2")
            values: 2D list of values to write
            value_input_option: 'RAW' or 'USER_ENTERED'

        Returns:
            True if successful
        """
        try:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueInputOption=value_input_option,
                body={'values': values}
            ).execute()
            return True
        except Exception as e:
            print(f"Error writing range: {e}", file=sys.stderr)
            return False

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_title: str,
        values: list[list],
        value_input_option: str = 'USER_ENTERED'
    ) -> bool:
        """
        Append rows to the end of a sheet.

        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_title: Sheet name
            values: 2D list of values to append
            value_input_option: 'RAW' or 'USER_ENTERED'

        Returns:
            True if successful
        """
        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A1",
                valueInputOption=value_input_option,
                insertDataOption='INSERT_ROWS',
                body={'values': values}
            ).execute()
            return True
        except Exception as e:
            print(f"Error appending rows: {e}", file=sys.stderr)
            return False

    # =========================================================================
    # Folder Operations
    # =========================================================================

    def get_folder_id(
        self,
        folder_path: str,
        create_if_missing: bool = False
    ) -> Optional[str]:
        """
        Get folder ID by path (supports nested paths).

        Args:
            folder_path: Folder path like "Folder/Subfolder/Target"
            create_if_missing: Create folders if not found

        Returns:
            Folder ID or None
        """
        parts = folder_path.split('/')
        parent_id = None

        for folder_name in parts:
            folder_name = folder_name.strip()
            if not folder_name:
                continue

            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                parent_id = files[0]['id']
            elif create_if_missing:
                # Create folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                if parent_id:
                    folder_metadata['parents'] = [parent_id]

                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                parent_id = folder['id']
            else:
                return None

        return parent_id

    def _move_to_folder(self, file_id: str, folder_id: str) -> bool:
        """Move a file to a folder."""
        try:
            # Get current parents
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            previous_parents = ','.join(file.get('parents', []))

            # Move to new folder
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            return True
        except Exception as e:
            print(f"Error moving file: {e}", file=sys.stderr)
            return False

    def list_spreadsheets(
        self,
        folder_id: str = None,
        max_results: int = 20
    ) -> list:
        """
        List Google Spreadsheets, optionally in a specific folder.

        Args:
            folder_id: Optional folder to list from
            max_results: Maximum number of results

        Returns:
            List of dicts with 'id', 'name', 'url'
        """
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = self.drive_service.files().list(
            q=query,
            pageSize=max_results,
            fields='files(id, name, modifiedTime)'
        ).execute()

        sheets = []
        for f in results.get('files', []):
            sheets.append({
                'id': f['id'],
                'name': f['name'],
                'url': f"https://docs.google.com/spreadsheets/d/{f['id']}/edit",
                'modified': f.get('modifiedTime', '')
            })
        return sheets

    # =========================================================================
    # Sheet Management Operations
    # =========================================================================

    def list_sheets(self, spreadsheet_id: str) -> list[dict]:
        """
        List all sheets in a spreadsheet.

        Args:
            spreadsheet_id: Spreadsheet ID

        Returns:
            List of dicts with 'id', 'title', 'index'
        """
        try:
            metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = []
            for sheet in metadata.get('sheets', []):
                props = sheet['properties']
                sheets.append({
                    'id': props['sheetId'],
                    'title': props['title'],
                    'index': props['index']
                })
            return sheets
        except Exception as e:
            print(f"Error listing sheets: {e}", file=sys.stderr)
            return []

    def get_sheet_id(self, spreadsheet_id: str, sheet_title: str) -> Optional[int]:
        """
        Get sheet ID by title.

        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_title: Sheet name

        Returns:
            Sheet ID or None
        """
        sheets = self.list_sheets(spreadsheet_id)
        for sheet in sheets:
            if sheet['title'] == sheet_title:
                return sheet['id']
        return None

    def add_sheet(
        self,
        spreadsheet_id: str,
        sheet_title: str,
        index: int = None
    ) -> Optional[int]:
        """
        Add a new blank sheet.

        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_title: New sheet name
            index: Optional position (0-based)

        Returns:
            New sheet ID or None
        """
        try:
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_title
                    }
                }
            }
            if index is not None:
                request['addSheet']['properties']['index'] = index

            result = self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()

            return result['replies'][0]['addSheet']['properties']['sheetId']
        except Exception as e:
            print(f"Error adding sheet: {e}", file=sys.stderr)
            return None

    def duplicate_sheet(
        self,
        spreadsheet_id: str,
        source_sheet_title: str,
        new_title: str,
        insert_index: int = None
    ) -> Optional[int]:
        """
        Duplicate an existing sheet.

        Args:
            spreadsheet_id: Spreadsheet ID
            source_sheet_title: Sheet to duplicate
            new_title: Name for the copy
            insert_index: Optional position for new sheet

        Returns:
            New sheet ID or None
        """
        try:
            # Get source sheet ID
            source_id = self.get_sheet_id(spreadsheet_id, source_sheet_title)
            if source_id is None:
                print(f"Sheet '{source_sheet_title}' not found", file=sys.stderr)
                return None

            request = {
                'duplicateSheet': {
                    'sourceSheetId': source_id,
                    'newSheetName': new_title
                }
            }
            if insert_index is not None:
                request['duplicateSheet']['insertSheetIndex'] = insert_index

            result = self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()

            return result['replies'][0]['duplicateSheet']['properties']['sheetId']
        except Exception as e:
            print(f"Error duplicating sheet: {e}", file=sys.stderr)
            return None

    def delete_sheet(self, spreadsheet_id: str, sheet_title: str) -> bool:
        """
        Delete a sheet by title.

        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_title: Sheet to delete

        Returns:
            True if successful
        """
        try:
            sheet_id = self.get_sheet_id(spreadsheet_id, sheet_title)
            if sheet_id is None:
                print(f"Sheet '{sheet_title}' not found", file=sys.stderr)
                return False

            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [{'deleteSheet': {'sheetId': sheet_id}}]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error deleting sheet: {e}", file=sys.stderr)
            return False

    def rename_sheet(
        self,
        spreadsheet_id: str,
        old_title: str,
        new_title: str
    ) -> bool:
        """
        Rename a sheet.

        Args:
            spreadsheet_id: Spreadsheet ID
            old_title: Current sheet name
            new_title: New sheet name

        Returns:
            True if successful
        """
        try:
            sheet_id = self.get_sheet_id(spreadsheet_id, old_title)
            if sheet_id is None:
                print(f"Sheet '{old_title}' not found", file=sys.stderr)
                return False

            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'title': new_title
                        },
                        'fields': 'title'
                    }
                }]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error renaming sheet: {e}", file=sys.stderr)
            return False


if __name__ == '__main__':
    print("Google Sheets Client - Testing connection...")
    client = GoogleSheetsClient()

    # List recent spreadsheets
    sheets = client.list_spreadsheets(max_results=5)
    print(f"Found {len(sheets)} recent spreadsheets:")
    for sheet in sheets:
        print(f"  - {sheet['name']}")
