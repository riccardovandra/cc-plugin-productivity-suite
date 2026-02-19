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
Gmail Read CLI

Read individual messages or full conversation threads.

Usage:
    python read.py --message-id <id>        # Read single message
    python read.py --thread-id <id>         # Read full conversation
    python read.py --thread-id <id> --output thread.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from gmail_client import GmailClient


def format_message(msg: dict, include_body: bool = True) -> str:
    """Format a message for display."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"From:    {msg['from']}")
    lines.append(f"To:      {msg['to']}")
    if msg.get('cc'):
        lines.append(f"CC:      {msg['cc']}")
    lines.append(f"Date:    {msg['date']}")
    lines.append(f"Subject: {msg['subject']}")
    lines.append(f"Labels:  {', '.join(msg.get('labels', []))}")
    lines.append("-" * 70)

    if include_body and msg.get('body'):
        body = msg['body']
        # Truncate very long bodies
        if len(body) > 5000:
            body = body[:5000] + "\n\n[... truncated, use --output for full text ...]"
        lines.append(body)
    elif not include_body:
        lines.append(f"[Snippet: {msg.get('snippet', '')}]")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Read Gmail messages or threads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python read.py --message-id 18abc123def  # Read single message
  python read.py --thread-id 18abc123def   # Read full thread
  python read.py --thread-id 18abc123def --output conversation.json
"""
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--message-id', '-m',
        type=str,
        help='Message ID to read'
    )
    group.add_argument(
        '--thread-id', '-t',
        type=str,
        help='Thread ID to read (full conversation)'
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
    parser.add_argument(
        '--no-body',
        action='store_true',
        help='Omit message bodies (show snippets only)'
    )

    args = parser.parse_args()

    client = GmailClient()

    # Read message or thread
    if args.message_id:
        print(f"Reading message: {args.message_id}", file=sys.stderr)
        msg = client.get_message(args.message_id)

        if not msg:
            print("Message not found.", file=sys.stderr)
            sys.exit(1)

        data = {
            'type': 'message',
            'fetched_at': datetime.now().isoformat(),
            'message': msg
        }

        if args.json or args.output:
            output = json.dumps(data, indent=2)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                with open(args.output, 'w') as f:
                    f.write(output)
                print(f"Saved to {args.output}", file=sys.stderr)
            else:
                print(output)
        else:
            print(format_message(msg, include_body=not args.no_body))

    else:  # thread_id
        print(f"Reading thread: {args.thread_id}", file=sys.stderr)
        thread = client.get_thread(args.thread_id)

        if not thread:
            print("Thread not found.", file=sys.stderr)
            sys.exit(1)

        print(f"Found {thread['message_count']} messages in thread", file=sys.stderr)

        data = {
            'type': 'thread',
            'fetched_at': datetime.now().isoformat(),
            'thread': thread
        }

        if args.json or args.output:
            output = json.dumps(data, indent=2)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                with open(args.output, 'w') as f:
                    f.write(output)
                print(f"Saved to {args.output}", file=sys.stderr)
            else:
                print(output)
        else:
            print(f"\nConversation ({thread['message_count']} messages)")
            print()
            for msg in thread['messages']:
                print(format_message(msg, include_body=not args.no_body))
                print()


if __name__ == '__main__':
    main()
