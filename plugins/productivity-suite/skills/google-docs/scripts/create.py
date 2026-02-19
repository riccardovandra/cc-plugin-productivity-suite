#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client>=2.0.0", "google-auth-oauthlib>=1.0.0"]
# ///
"""
Create Google Doc from Markdown

Converts a markdown file to a new Google Doc with formatting preserved.

Usage:
    python create.py input.md --title "My Document"
    python create.py input.md --folder "Reports"
    python create.py input.md --title "Report" --folder "Work/Reports"
"""

import argparse
import sys
from pathlib import Path

from docs_client import GoogleDocsClient, MarkdownToDocsConverter


def create_doc_from_markdown(
    input_path: str,
    title: str = None,
    folder: str = None
) -> dict:
    """
    Create a Google Doc from a markdown file.

    Args:
        input_path: Path to markdown file
        title: Document title (defaults to filename)
        folder: Folder name to create doc in (optional)

    Returns:
        Dict with 'id', 'title', 'url'
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read markdown content
    content = input_file.read_text(encoding='utf-8')

    # Default title from filename
    if not title:
        title = input_file.stem

    # Initialize client
    client = GoogleDocsClient()

    # Get folder ID if specified
    folder_id = None
    if folder:
        folder_id = client.get_folder_id(folder, create_if_missing=True)
        if folder_id:
            print(f"Using folder: {folder}")

    # Create empty document
    doc = client.create_document(title, folder_id)
    print(f"Created document: {doc['title']}")

    # Convert markdown to Docs API requests
    converter = MarkdownToDocsConverter()
    requests = converter.convert(content)

    # Phase 1: Apply text formatting
    if requests:
        success = client.batch_update(doc['id'], requests)
        if not success:
            print("Warning: Some formatting may not have been applied", file=sys.stderr)

    # Phase 2: Insert native tables (if any)
    pending_tables = converter.get_pending_tables()
    if pending_tables:
        success = client.insert_tables(doc['id'], pending_tables)
        if not success:
            print("Warning: Some tables may not have been inserted", file=sys.stderr)

    print(f"URL: {doc['url']}")
    return doc


def main():
    parser = argparse.ArgumentParser(
        description="Create Google Doc from Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create.py document.md
  python create.py document.md --title "My Document"
  python create.py report.md --title "Q4 Report" --folder "Reports"
"""
    )

    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('--title', '-t', help='Document title (default: filename)')
    parser.add_argument('--folder', '-f', help='Google Drive folder name')

    args = parser.parse_args()

    result = create_doc_from_markdown(
        input_path=args.input,
        title=args.title,
        folder=args.folder
    )

    # Output JSON for programmatic use
    print(f"\nDocument ID: {result['id']}")


if __name__ == '__main__':
    main()
