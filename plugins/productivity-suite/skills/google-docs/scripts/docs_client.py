#!/usr/bin/env python3
"""
Google Docs API Client

Core API wrapper for Google Docs operations.
Used by other scripts in this skill.

Usage:
    from docs_client import GoogleDocsClient

    client = GoogleDocsClient()
    doc = client.create_document("My Document")
    client.insert_text(doc['id'], "Hello World")
"""

import re
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

from google_auth import get_docs_credentials


class GoogleDocsClient:
    """Google Docs API client wrapper."""

    def __init__(self):
        """Initialize Google Docs client with Docs and Drive services."""
        credentials = get_docs_credentials()
        self.docs_service = build('docs', 'v1', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)

    # =========================================================================
    # Document Operations
    # =========================================================================

    def create_document(self, title: str, folder_id: str = None) -> dict:
        """
        Create a new Google Doc.

        Args:
            title: Document title
            folder_id: Optional folder ID to create doc in

        Returns:
            Dict with 'id', 'title', 'url'
        """
        # Create the document
        doc = self.docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']

        # Move to folder if specified
        if folder_id:
            # Get current parents
            file = self.drive_service.files().get(
                fileId=doc_id,
                fields='parents'
            ).execute()
            previous_parents = ",".join(file.get('parents', []))

            # Move to new folder
            self.drive_service.files().update(
                fileId=doc_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

        return {
            'id': doc_id,
            'title': title,
            'url': f"https://docs.google.com/document/d/{doc_id}/edit"
        }

    def get_document(self, doc_id: str) -> Optional[dict]:
        """
        Get document metadata and content structure.

        Args:
            doc_id: Document ID

        Returns:
            Document object or None if not found
        """
        try:
            return self.docs_service.documents().get(documentId=doc_id).execute()
        except Exception as e:
            print(f"Error getting document {doc_id}: {e}", file=sys.stderr)
            return None

    def get_document_text(self, doc_id: str) -> str:
        """
        Extract plain text content from a document.

        Args:
            doc_id: Document ID

        Returns:
            Plain text content
        """
        doc = self.get_document(doc_id)
        if not doc:
            return ""

        text = ""
        content = doc.get('body', {}).get('content', [])
        for element in content:
            if 'paragraph' in element:
                for elem in element['paragraph'].get('elements', []):
                    if 'textRun' in elem:
                        text += elem['textRun'].get('content', '')
        return text

    def clear_document(self, doc_id: str) -> bool:
        """
        Clear all content from a document.

        Args:
            doc_id: Document ID

        Returns:
            True if successful
        """
        doc = self.get_document(doc_id)
        if not doc:
            return False

        content = doc.get('body', {}).get('content', [])
        if len(content) <= 1:
            return True  # Already empty

        # Find end index (last character before final newline)
        end_index = 1
        for element in content:
            if 'endIndex' in element:
                end_index = max(end_index, element['endIndex'])

        if end_index <= 1:
            return True

        # Delete content (keep index 1, the starting newline)
        requests = [{
            'deleteContentRange': {
                'range': {
                    'startIndex': 1,
                    'endIndex': end_index - 1
                }
            }
        }]

        try:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            return True
        except Exception as e:
            print(f"Error clearing document: {e}", file=sys.stderr)
            return False

    def batch_update(self, doc_id: str, requests: list) -> bool:
        """
        Execute batch update requests on a document.

        Args:
            doc_id: Document ID
            requests: List of request objects

        Returns:
            True if successful
        """
        if not requests:
            return True

        try:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            return True
        except Exception as e:
            print(f"Error updating document: {e}", file=sys.stderr)
            return False

    def insert_tables(self, doc_id: str, tables: list) -> bool:
        """
        Insert native Google Docs tables (two-phase: structure then content).

        Args:
            doc_id: Document ID
            tables: List of table data (each is list of rows)

        Returns:
            True if successful
        """
        if not tables:
            return True

        try:
            for table_rows in tables:
                num_rows = len(table_rows)
                num_cols = max(len(row) for row in table_rows) if table_rows else 0

                if num_rows == 0 or num_cols == 0:
                    continue

                # Phase 1: Insert empty table at end of document
                insert_request = [{
                    'insertTable': {
                        'endOfSegmentLocation': {'segmentId': ''},
                        'rows': num_rows,
                        'columns': num_cols
                    }
                }]

                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': insert_request}
                ).execute()

                # Phase 2: Get document structure to find cell indices
                doc = self.docs_service.documents().get(documentId=doc_id).execute()
                body = doc.get('body', {}).get('content', [])

                # Find the table we just inserted (last table in document)
                table_element = None
                for element in reversed(body):
                    if 'table' in element:
                        table_element = element
                        break

                if not table_element:
                    print("Warning: Could not find inserted table", file=sys.stderr)
                    continue

                # Phase 3: Insert content into cells
                cell_requests = []
                table = table_element['table']

                for row_idx, row_data in enumerate(table.get('tableRows', [])):
                    for col_idx, cell_data in enumerate(row_data.get('tableCells', [])):
                        if row_idx < len(table_rows) and col_idx < len(table_rows[row_idx]):
                            cell_text = str(table_rows[row_idx][col_idx])
                            if cell_text:
                                # Get the paragraph start index in this cell
                                cell_content = cell_data.get('content', [])
                                if cell_content:
                                    para_start = cell_content[0].get('startIndex', 0)
                                    cell_requests.append({
                                        'insertText': {
                                            'location': {'index': para_start},
                                            'text': cell_text
                                        }
                                    })

                # Apply cell content (reverse order to preserve indices)
                if cell_requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': list(reversed(cell_requests))}
                    ).execute()

                # Phase 4: Bold header row
                doc = self.docs_service.documents().get(documentId=doc_id).execute()
                body = doc.get('body', {}).get('content', [])

                for element in reversed(body):
                    if 'table' in element:
                        table = element['table']
                        first_row = table.get('tableRows', [])[0] if table.get('tableRows') else None
                        if first_row:
                            bold_requests = []
                            for cell_data in first_row.get('tableCells', []):
                                cell_content = cell_data.get('content', [])
                                if cell_content:
                                    start_idx = cell_content[0].get('startIndex', 0)
                                    end_idx = cell_content[0].get('endIndex', start_idx + 1)
                                    if end_idx > start_idx + 1:  # Has content
                                        bold_requests.append({
                                            'updateTextStyle': {
                                                'range': {'startIndex': start_idx, 'endIndex': end_idx - 1},
                                                'textStyle': {'bold': True},
                                                'fields': 'bold'
                                            }
                                        })
                            if bold_requests:
                                self.docs_service.documents().batchUpdate(
                                    documentId=doc_id,
                                    body={'requests': bold_requests}
                                ).execute()
                        break

            return True

        except Exception as e:
            print(f"Error inserting tables: {e}", file=sys.stderr)
            return False

    # =========================================================================
    # Folder Operations
    # =========================================================================

    def get_folder_id(self, folder_name: str, create_if_missing: bool = True) -> Optional[str]:
        """
        Get folder ID by name, optionally creating if missing.

        Args:
            folder_name: Folder name to find
            create_if_missing: Create folder if not found

        Returns:
            Folder ID or None
        """
        # Search for folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])
        if files:
            return files[0]['id']

        if create_if_missing:
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            return folder['id']

        return None

    def list_documents(self, folder_id: str = None, max_results: int = 20) -> list:
        """
        List Google Docs, optionally in a specific folder.

        Args:
            folder_id: Optional folder to list from
            max_results: Maximum number of results

        Returns:
            List of dicts with 'id', 'name', 'url'
        """
        query = "mimeType='application/vnd.google-apps.document' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = self.drive_service.files().list(
            q=query,
            pageSize=max_results,
            fields='files(id, name, modifiedTime)'
        ).execute()

        docs = []
        for f in results.get('files', []):
            docs.append({
                'id': f['id'],
                'name': f['name'],
                'url': f"https://docs.google.com/document/d/{f['id']}/edit",
                'modified': f.get('modifiedTime', '')
            })
        return docs


class MarkdownToDocsConverter:
    """Convert markdown content to Google Docs API requests."""

    def __init__(self):
        self.index = 1  # Google Docs starts at index 1
        self.requests = []

    def convert(self, markdown_content: str) -> list:
        """
        Convert markdown to Google Docs API requests.

        Args:
            markdown_content: Markdown text

        Returns:
            List of API request objects
        """
        self.index = 1
        self.requests = []

        lines = markdown_content.split('\n')
        i = 0
        in_code_block = False
        code_lines = []
        in_table = False
        table_rows = []

        while i < len(lines):
            line = lines[i]

            # Code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    self._add_code_block(code_lines)
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Tables
            if '|' in line and line.strip().startswith('|'):
                if re.match(r'^\|[\s\-:]+\|', line.strip()):
                    i += 1
                    continue
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    if not in_table:
                        in_table = True
                        table_rows = []
                    table_rows.append(cells)
                i += 1
                continue
            elif in_table:
                self._add_table(table_rows)
                table_rows = []
                in_table = False

            # Headers (check longest first to avoid partial matches)
            if line.startswith('#### '):
                self._add_heading(line[5:].strip(), 'HEADING_4')
            elif line.startswith('### '):
                self._add_heading(line[4:].strip(), 'HEADING_3')
            elif line.startswith('## '):
                self._add_heading(line[3:].strip(), 'HEADING_2')
            elif line.startswith('# '):
                self._add_heading(line[2:].strip(), 'HEADING_1')

            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                self._add_horizontal_rule()

            # Bullet lists
            elif re.match(r'^(\s*)[-*]\s+', line):
                match = re.match(r'^(\s*)[-*]\s+(.+)', line)
                if match:
                    indent = len(match.group(1)) // 2
                    self._add_bullet(match.group(2), indent)

            # Numbered lists
            elif re.match(r'^(\s*)\d+\.\s+', line):
                match = re.match(r'^(\s*)\d+\.\s+(.+)', line)
                if match:
                    indent = len(match.group(1)) // 2
                    self._add_numbered(match.group(2), indent)

            # Paragraphs
            elif line.strip():
                self._add_paragraph(line.strip())

            i += 1

        # Handle remaining table
        if in_table and table_rows:
            self._add_table(table_rows)

        return self.requests

    def _add_text(self, text: str) -> tuple:
        """Insert text and return (start_index, end_index)."""
        start = self.index
        self.requests.append({
            'insertText': {
                'location': {'index': self.index},
                'text': text
            }
        })
        self.index += len(text)
        return (start, self.index)

    def _add_heading(self, text: str, style: str):
        """Add a heading."""
        text_with_newline = text + '\n'
        start, end = self._add_text(text_with_newline)

        self.requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': start, 'endIndex': end},
                'paragraphStyle': {'namedStyleType': style},
                'fields': 'namedStyleType'
            }
        })

    def _add_paragraph(self, text: str):
        """Add a paragraph with inline formatting."""
        # Find bold and italic spans before inserting
        formatted_text, format_spans = self._parse_inline_formatting(text)
        text_with_newline = formatted_text + '\n'
        start, end = self._add_text(text_with_newline)

        # Apply formatting
        for span_start, span_end, style in format_spans:
            abs_start = start + span_start
            abs_end = start + span_end
            self.requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': abs_start, 'endIndex': abs_end},
                    'textStyle': style,
                    'fields': ','.join(style.keys())
                }
            })

    def _parse_inline_formatting(self, text: str) -> tuple:
        """Parse inline markdown and return (clean_text, format_spans)."""
        spans = []
        result = ""
        i = 0

        while i < len(text):
            # Bold **text**
            if text[i:i+2] == '**':
                end = text.find('**', i + 2)
                if end != -1:
                    content = text[i+2:end]
                    spans.append((len(result), len(result) + len(content), {'bold': True}))
                    result += content
                    i = end + 2
                    continue

            # Italic *text*
            if text[i] == '*' and (i == 0 or text[i-1] != '*') and (i + 1 < len(text) and text[i+1] != '*'):
                end = text.find('*', i + 1)
                if end != -1 and (end + 1 >= len(text) or text[end+1] != '*'):
                    content = text[i+1:end]
                    spans.append((len(result), len(result) + len(content), {'italic': True}))
                    result += content
                    i = end + 1
                    continue

            # Inline code `text`
            if text[i] == '`':
                end = text.find('`', i + 1)
                if end != -1:
                    content = text[i+1:end]
                    spans.append((len(result), len(result) + len(content), {
                        'weightedFontFamily': {'fontFamily': 'Courier New'}
                    }))
                    result += content
                    i = end + 1
                    continue

            result += text[i]
            i += 1

        return result, spans

    def _add_bullet(self, text: str, nesting_level: int = 0):
        """Add a bullet list item."""
        formatted_text, format_spans = self._parse_inline_formatting(text)
        text_with_newline = formatted_text + '\n'
        start, end = self._add_text(text_with_newline)

        self.requests.append({
            'createParagraphBullets': {
                'range': {'startIndex': start, 'endIndex': end},
                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
            }
        })

        if nesting_level > 0:
            self.requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'paragraphStyle': {'indentStart': {'magnitude': 36 * nesting_level, 'unit': 'PT'}},
                    'fields': 'indentStart'
                }
            })

        # Apply inline formatting
        for span_start, span_end, style in format_spans:
            abs_start = start + span_start
            abs_end = start + span_end
            self.requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': abs_start, 'endIndex': abs_end},
                    'textStyle': style,
                    'fields': ','.join(style.keys())
                }
            })

    def _add_numbered(self, text: str, nesting_level: int = 0):
        """Add a numbered list item."""
        formatted_text, format_spans = self._parse_inline_formatting(text)
        text_with_newline = formatted_text + '\n'
        start, end = self._add_text(text_with_newline)

        self.requests.append({
            'createParagraphBullets': {
                'range': {'startIndex': start, 'endIndex': end},
                'bulletPreset': 'NUMBERED_DECIMAL_ALPHA_ROMAN'
            }
        })

        if nesting_level > 0:
            self.requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'paragraphStyle': {'indentStart': {'magnitude': 36 * nesting_level, 'unit': 'PT'}},
                    'fields': 'indentStart'
                }
            })

        # Apply inline formatting
        for span_start, span_end, style in format_spans:
            abs_start = start + span_start
            abs_end = start + span_end
            self.requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': abs_start, 'endIndex': abs_end},
                    'textStyle': style,
                    'fields': ','.join(style.keys())
                }
            })

    def _add_code_block(self, lines: list):
        """Add a code block with monospace formatting."""
        code_text = '\n'.join(lines) + '\n'
        start, end = self._add_text(code_text)

        # Apply monospace font
        self.requests.append({
            'updateTextStyle': {
                'range': {'startIndex': start, 'endIndex': end},
                'textStyle': {
                    'weightedFontFamily': {'fontFamily': 'Courier New'},
                    'fontSize': {'magnitude': 10, 'unit': 'PT'}
                },
                'fields': 'weightedFontFamily,fontSize'
            }
        })

        # Add background color (light gray)
        self.requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': start, 'endIndex': end},
                'paragraphStyle': {
                    'shading': {'backgroundColor': {'color': {'rgbColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}}}}
                },
                'fields': 'shading'
            }
        })

    def _add_table(self, rows: list):
        """Store table for two-phase insertion."""
        if not rows:
            return

        if not hasattr(self, 'pending_tables'):
            self.pending_tables = []

        self.pending_tables.append(rows)

        # Add placeholder text for table position
        self._add_text('[TABLE]\n')

    def get_pending_tables(self) -> list:
        """Get list of pending tables."""
        return getattr(self, 'pending_tables', [])

    def _add_horizontal_rule(self):
        """Add a horizontal rule (as dashes for now, since Docs doesn't have native HR)."""
        self._add_text('---\n')


if __name__ == '__main__':
    print("Google Docs Client - Testing connection...")
    client = GoogleDocsClient()

    # List recent docs
    docs = client.list_documents(max_results=5)
    print(f"Found {len(docs)} recent documents:")
    for doc in docs:
        print(f"  - {doc['name']}")
