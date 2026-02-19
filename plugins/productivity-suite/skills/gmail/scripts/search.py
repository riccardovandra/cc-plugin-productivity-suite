#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client>=2.100.0",
#     "google-auth-oauthlib>=1.1.0",
#     "markdown>=3.5.0",
# ]
# ///
"""
Gmail Search CLI

Search and list emails using Gmail search syntax.

Usage:
    python search.py                        # List recent inbox messages
    python search.py --query "from:client"  # Search with query
    python search.py --unread               # Show only unread
    python search.py --limit 50             # Get more results
    python search.py --output results.json  # Save to file
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from gmail_client import GmailClient


def format_message_row(msg: dict, width: int = 80) -> str:
    """Format a message for display."""
    # Extract sender name/email
    sender = msg['from']
    if '<' in sender:
        sender = sender.split('<')[0].strip().strip('"')
    sender = sender[:25].ljust(25)

    # Subject
    subject = msg['subject'][:40].ljust(40)

    # Date
    date = msg['date'].split(' ')[0] if msg['date'] else ''

    return f"{date}  {sender}  {subject}"


def main():
    parser = argparse.ArgumentParser(
        description="Search Gmail messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Gmail Search Operators:
  from:sender         Messages from sender
  to:recipient        Messages to recipient
  subject:word        Messages with word in subject
  is:unread           Unread messages
  is:starred          Starred messages
  has:attachment      Messages with attachments
  after:2024/01/01    Messages after date
  before:2024/12/31   Messages before date
  label:work          Messages with label
  in:inbox            Messages in inbox
  -keyword            Exclude keyword

Examples:
  python search.py --query "from:client@example.com is:unread"
  python search.py --query "subject:invoice after:2024/01/01"
  python search.py --query "has:attachment from:accounts"
"""
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        default='in:inbox',
        help='Gmail search query (default: in:inbox)'
    )
    parser.add_argument(
        '--unread',
        action='store_true',
        help='Show only unread messages'
    )
    parser.add_argument(
        '--limit', '-n',
        type=int,
        default=20,
        help='Maximum messages to return (default: 20)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON to stdout'
    )

    args = parser.parse_args()

    # Build query
    query = args.query
    if args.unread and 'is:unread' not in query:
        query = f"{query} is:unread"

    print(f"Searching: {query}", file=sys.stderr)

    # Search
    client = GmailClient()
    messages = client.search(query=query, max_results=args.limit)

    if not messages:
        print("No messages found.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(messages)} messages", file=sys.stderr)

    # Output
    if args.json or args.output:
        output_data = {
            'query': query,
            'searched_at': datetime.now().isoformat(),
            'count': len(messages),
            'messages': messages
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"Saved to {output_path}", file=sys.stderr)
        else:
            print(json.dumps(output_data, indent=2))
    else:
        # Table output
        print()
        print("DATE        SENDER                     SUBJECT")
        print("-" * 80)
        for msg in messages:
            print(format_message_row(msg))
            # Show message ID and thread ID for reference
            print(f"            ID: {msg['id']}  Thread: {msg['thread_id']}")
        print()


if __name__ == '__main__':
    main()
