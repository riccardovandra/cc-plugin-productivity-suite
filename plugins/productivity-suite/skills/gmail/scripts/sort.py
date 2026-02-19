#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client>=2.100.0",
#     "google-auth-oauthlib>=1.1.0",
#     "python-dateutil>=2.8.0",
#     "markdown>=3.5.0",
# ]
# ///
"""
Gmail Sort CLI

Archive, snooze, label, and mark emails as read.

Usage:
    python sort.py archive <message_id>           # Archive message
    python sort.py archive-thread <thread_id>     # Archive whole thread
    python sort.py snooze <message_id> --until "tomorrow 9am"
    python sort.py label <message_id> --label "Follow-up"
    python sort.py unlabel <message_id> --label "Follow-up"
    python sort.py mark-read <message_id>         # Mark as read
    python sort.py mark-read-thread <thread_id>   # Mark thread as read
"""

import argparse
import sys
from datetime import datetime, timedelta
from dateutil import parser as dateparser

from gmail_client import GmailClient


def parse_snooze_time(time_str: str) -> datetime:
    """Parse natural language time into datetime."""
    time_str = time_str.lower()

    now = datetime.now()

    # Handle relative times
    if 'tomorrow' in time_str:
        base = now + timedelta(days=1)
        # Extract time if present
        if 'morning' in time_str or '9am' in time_str or '9 am' in time_str:
            return base.replace(hour=9, minute=0, second=0)
        elif 'afternoon' in time_str or '2pm' in time_str:
            return base.replace(hour=14, minute=0, second=0)
        elif 'evening' in time_str or '6pm' in time_str:
            return base.replace(hour=18, minute=0, second=0)
        else:
            return base.replace(hour=9, minute=0, second=0)

    elif 'monday' in time_str:
        days_ahead = (0 - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0)

    elif 'next week' in time_str:
        return (now + timedelta(days=7)).replace(hour=9, minute=0, second=0)

    elif 'hour' in time_str:
        try:
            hours = int(''.join(filter(str.isdigit, time_str.split('hour')[0])) or '1')
            return now + timedelta(hours=hours)
        except:
            return now + timedelta(hours=1)

    else:
        # Try to parse as datetime
        try:
            return dateparser.parse(time_str)
        except:
            print(f"Could not parse time: {time_str}", file=sys.stderr)
            print("Using 'tomorrow 9am'", file=sys.stderr)
            return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0)


def main():
    parser = argparse.ArgumentParser(
        description="Sort Gmail messages (archive, snooze, label)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  archive <message_id>        Remove from inbox
  archive-thread <thread_id>  Archive all messages in thread
  snooze <message_id>         Snooze message (archives with reminder)
  label <message_id>          Add a label
  unlabel <message_id>        Remove a label

Examples:
  python sort.py archive 18abc123def
  python sort.py archive-thread 18abc123def
  python sort.py snooze 18abc123def --until "tomorrow 9am"
  python sort.py snooze 18abc123def --until "monday morning"
  python sort.py label 18abc123def --label "Follow-up"
  python sort.py unlabel 18abc123def --label "INBOX"
"""
    )

    parser.add_argument(
        'command',
        choices=['archive', 'archive-thread', 'snooze', 'label', 'unlabel', 'mark-read', 'mark-read-thread'],
        help='Action to perform'
    )
    parser.add_argument(
        'id',
        help='Message ID or Thread ID'
    )
    parser.add_argument(
        '--until', '-u',
        type=str,
        help='Snooze until time (e.g., "tomorrow 9am", "monday", "2 hours")'
    )
    parser.add_argument(
        '--label', '-l',
        type=str,
        help='Label name for label/unlabel commands'
    )

    args = parser.parse_args()

    client = GmailClient()

    if args.command == 'archive':
        print(f"Archiving message: {args.id}")
        if client.archive(args.id):
            print("Archived successfully.")
        else:
            print("Failed to archive.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'archive-thread':
        print(f"Archiving thread: {args.id}")
        if client.archive_thread(args.id):
            print("Thread archived successfully.")
        else:
            print("Failed to archive thread.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'snooze':
        if not args.until:
            print("Error: --until is required for snooze", file=sys.stderr)
            print("Example: --until 'tomorrow 9am'", file=sys.stderr)
            sys.exit(1)

        snooze_time = parse_snooze_time(args.until)
        print(f"Snoozing message until: {snooze_time.strftime('%Y-%m-%d %H:%M')}")

        if client.snooze(args.id, snooze_time):
            print("Message snoozed (archived).")
            print(f"Reminder: Check back at {snooze_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("Failed to snooze.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'label':
        if not args.label:
            print("Error: --label is required", file=sys.stderr)
            sys.exit(1)

        print(f"Adding label '{args.label}' to message: {args.id}")
        if client.add_label(args.id, args.label):
            print(f"Label '{args.label}' added.")
        else:
            print("Failed to add label.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'unlabel':
        if not args.label:
            print("Error: --label is required", file=sys.stderr)
            sys.exit(1)

        print(f"Removing label '{args.label}' from message: {args.id}")
        if client.remove_label(args.id, args.label):
            print(f"Label '{args.label}' removed.")
        else:
            print("Failed to remove label.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'mark-read':
        print(f"Marking message as read: {args.id}")
        if client.remove_label(args.id, 'UNREAD'):
            print("Marked as read.")
        else:
            print("Failed to mark as read.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'mark-read-thread':
        print(f"Marking thread as read: {args.id}")
        if client.mark_thread_read(args.id):
            print("Thread marked as read.")
        else:
            print("Failed to mark thread as read.", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
