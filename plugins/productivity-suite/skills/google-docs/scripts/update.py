#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client>=2.0.0", "google-auth-oauthlib>=1.0.0"]
# ///
"""
Update Google Doc from Markdown

Updates an existing Google Doc with new markdown content.

Usage:
    python update.py input.md --doc-id "1abc123..."
    python update.py input.md --doc-url "https://docs.google.com/document/d/1abc123.../edit"
    python update.py input.md --doc-id "1abc123..." --append
"""

import argparse
import re
import sys
from pathlib import Path

from docs_client import GoogleDocsClient, MarkdownToDocsConverter


def extract_doc_id(doc_id_or_url: str) -> str:
    """
    Extract document ID from URL or return as-is if already an ID.

    Args:
        doc_id_or_url: Document ID or Google Docs URL

    Returns:
        Document ID
    """
    # Check if it's a URL
    if doc_id_or_url.startswith('http'):
        # Extract ID from URL like https://docs.google.com/document/d/DOC_ID/edit
        match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_id_or_url)
        if match:
            return match.group(1)
        raise ValueError(f"Could not extract document ID from URL: {doc_id_or_url}")
    return doc_id_or_url


def update_doc_from_markdown(
    input_path: str,
    doc_id: str = None,
    doc_url: str = None,
    append: bool = False
) -> dict:
    """
    Update a Google Doc from a markdown file.

    Args:
        input_path: Path to markdown file
        doc_id: Document ID (or use doc_url)
        doc_url: Document URL (alternative to doc_id)
        append: If True, append to existing content instead of replacing

    Returns:
        Dict with 'id', 'url', 'success'
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Get document ID
    if doc_url:
        doc_id = extract_doc_id(doc_url)
    elif doc_id:
        doc_id = extract_doc_id(doc_id)
    else:
        print("Error: Must provide --doc-id or --doc-url", file=sys.stderr)
        sys.exit(1)

    # Read markdown content
    content = input_file.read_text(encoding='utf-8')

    # Initialize client
    client = GoogleDocsClient()

    # Verify document exists
    doc = client.get_document(doc_id)
    if not doc:
        print(f"Error: Document not found: {doc_id}", file=sys.stderr)
        sys.exit(1)

    print(f"Updating document: {doc.get('title', 'Untitled')}")

    # Clear existing content if not appending
    if not append:
        success = client.clear_document(doc_id)
        if not success:
            print("Warning: Could not clear existing content", file=sys.stderr)

    # Convert markdown to Docs API requests
    converter = MarkdownToDocsConverter()
    requests = converter.convert(content)

    # Apply formatting
    success = True
    if requests:
        success = client.batch_update(doc_id, requests)
        if not success:
            print("Warning: Some formatting may not have been applied", file=sys.stderr)

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"Updated: {url}")

    return {
        'id': doc_id,
        'url': url,
        'success': success
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update Google Doc from Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update.py document.md --doc-id "1abc123..."
  python update.py document.md --doc-url "https://docs.google.com/document/d/1abc123.../edit"
  python update.py changes.md --doc-id "1abc123..." --append
"""
    )

    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('--doc-id', '-d', help='Document ID')
    parser.add_argument('--doc-url', '-u', help='Document URL')
    parser.add_argument('--append', '-a', action='store_true',
                        help='Append to existing content instead of replacing')

    args = parser.parse_args()

    if not args.doc_id and not args.doc_url:
        parser.error("Must provide either --doc-id or --doc-url")

    result = update_doc_from_markdown(
        input_path=args.input,
        doc_id=args.doc_id,
        doc_url=args.doc_url,
        append=args.append
    )

    if result['success']:
        print("\nUpdate complete!")
    else:
        print("\nUpdate completed with warnings", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
