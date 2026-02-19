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
Gmail Draft CLI

Create draft emails (does NOT send).

Usage:
    python draft.py create --to "person@example.com" --subject "Hello" --body body.txt
    python draft.py reply --thread-id <id> --body reply.txt
    python draft.py list
    python draft.py delete <draft_id>
"""

import argparse
import sys
from pathlib import Path

from gmail_client import GmailClient


def main():
    parser = argparse.ArgumentParser(
        description="Create Gmail drafts (does NOT send)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  create                 Create new draft
  reply                  Create reply draft in thread
  list                   List existing drafts
  delete <draft_id>      Delete a draft

Examples:
  # Create new draft
  python draft.py create --to "person@example.com" --subject "Meeting" --body message.txt

  # Reply to thread
  python draft.py reply --thread-id 18abc123def --body reply.txt

  # Create with inline body
  echo "Hello world" | python draft.py create --to "x@y.com" --subject "Test" --body -

  # List drafts
  python draft.py list

IMPORTANT: This creates DRAFTS only. To send, open Gmail and send manually.
"""
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Create command
    create_parser = subparsers.add_parser('create', help='Create new draft')
    create_parser.add_argument('--to', '-t', required=True, help='Recipient email')
    create_parser.add_argument('--subject', '-s', required=True, help='Email subject')
    create_parser.add_argument('--body', '-b', required=True, help='Body text file (or - for stdin)')
    create_parser.add_argument('--cc', help='CC recipients')
    create_parser.add_argument('--bcc', help='BCC recipients')
    create_parser.add_argument('--attach', '-a', action='append', help='File to attach (can be used multiple times)')
    create_parser.add_argument('--thread-id', help='Thread ID to add this message to (for replies)')

    # Reply command
    reply_parser = subparsers.add_parser('reply', help='Create reply draft')
    reply_parser.add_argument('--thread-id', '-t', required=True, help='Thread ID to reply to')
    reply_parser.add_argument('--body', '-b', required=True, help='Body text file (or - for stdin)')
    reply_parser.add_argument('--attach', '-a', action='append', help='File to attach (can be used multiple times)')

    # List command
    list_parser = subparsers.add_parser('list', help='List drafts')
    list_parser.add_argument('--limit', '-n', type=int, default=10, help='Max drafts to show')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a draft')
    delete_parser.add_argument('draft_id', help='Draft ID to delete')

    args = parser.parse_args()

    client = GmailClient()

    if args.command == 'create':
        # Read body
        if args.body == '-':
            body = sys.stdin.read()
        else:
            body_path = Path(args.body)
            if not body_path.exists():
                print(f"Error: Body file not found: {args.body}", file=sys.stderr)
                sys.exit(1)
            body = body_path.read_text()

        print(f"Creating draft...")
        print(f"  To: {args.to}")
        print(f"  Subject: {args.subject}")
        if args.cc:
            print(f"  CC: {args.cc}")
        if args.thread_id:
            print(f"  Thread: {args.thread_id}")
        if args.attach:
            print(f"  Attachments: {len(args.attach)} file(s)")
            for f in args.attach:
                print(f"    - {f}")

        draft = client.create_draft(
            to=args.to,
            subject=args.subject,
            body=body,
            cc=args.cc,
            bcc=args.bcc,
            attachments=args.attach,
            thread_id=args.thread_id
        )

        if draft:
            print()
            print("Draft created successfully!")
            print(f"  Draft ID: {draft['id']}")
            print()
            print("IMPORTANT: This is a DRAFT. Open Gmail to send.")
        else:
            print("Failed to create draft.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'reply':
        # Get thread info first
        thread = client.get_thread(args.thread_id)
        if not thread:
            print(f"Thread not found: {args.thread_id}", file=sys.stderr)
            sys.exit(1)

        # Get last message to determine reply subject and recipient
        last_msg = thread['messages'][-1]
        subject = last_msg['subject']
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"

        # Determine recipient
        # If last message was sent BY me (has SENT label), reply to the 'to' field
        # Otherwise, reply to the sender
        import re

        is_sent_by_me = 'SENT' in last_msg.get('labels', [])

        if is_sent_by_me:
            # I sent the last message, so reply to the original recipient
            to = last_msg['to']
        else:
            # Someone else sent the last message, reply to them
            to = last_msg['from']

        # Extract email from "Name <email>" format
        if '<' in to:
            match = re.search(r'<([^>]+)>', to)
            if match:
                to = match.group(1)

        # Read body
        if args.body == '-':
            body = sys.stdin.read()
        else:
            body_path = Path(args.body)
            if not body_path.exists():
                print(f"Error: Body file not found: {args.body}", file=sys.stderr)
                sys.exit(1)
            body = body_path.read_text()

        print(f"Creating reply draft...")
        print(f"  To: {to}")
        print(f"  Subject: {subject}")
        print(f"  Thread: {args.thread_id}")
        if args.attach:
            print(f"  Attachments: {len(args.attach)} file(s)")
            for f in args.attach:
                print(f"    - {f}")

        draft = client.create_draft(
            to=to,
            subject=subject,
            body=body,
            thread_id=args.thread_id,
            attachments=args.attach
        )

        if draft:
            print()
            print("Reply draft created successfully!")
            print(f"  Draft ID: {draft['id']}")
            print()
            print("IMPORTANT: This is a DRAFT. Open Gmail to send.")
        else:
            print("Failed to create draft.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'list':
        drafts = client.list_drafts(max_results=args.limit)

        if not drafts:
            print("No drafts found.")
            return

        print(f"Found {len(drafts)} drafts:")
        print()
        for draft in drafts:
            draft_id = draft['id']
            msg_id = draft.get('message', {}).get('id', 'N/A')
            print(f"  Draft ID: {draft_id}")
            print(f"  Message ID: {msg_id}")
            print()

    elif args.command == 'delete':
        print(f"Deleting draft: {args.draft_id}")
        if client.delete_draft(args.draft_id):
            print("Draft deleted.")
        else:
            print("Failed to delete draft.", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
