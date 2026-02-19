#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["slack-sdk>=3.27.0"]
# ///
"""
Read Slack Conversations

Read message history from channels, DMs, or threads.

Usage:
    uv run read.py --channel C1234567890
    uv run read.py --channel C1234567890 --limit 50
    uv run read.py --channel C1234567890 --thread 1234567890.123456
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent for slack_client
sys.path.insert(0, str(Path(__file__).parent))
from slack_client import SlackClient


def format_message(msg: dict, show_id: bool = False) -> str:
    """Format a message for display."""
    lines = []

    # Header: user and date
    header = f"**{msg['user_name']}** ({msg['date']})"
    if msg.get('reply_count', 0) > 0:
        header += f" - {msg['reply_count']} replies"
    lines.append(header)

    # Message text
    text = msg['text']
    if text:
        # Indent message body
        for line in text.split('\n'):
            lines.append(f"  {line}")

    # Reactions
    if msg.get('reactions'):
        reactions = ' '.join([f":{r['name']}: {r['count']}" for r in msg['reactions']])
        lines.append(f"  [{reactions}]")

    # ID for reference
    if show_id:
        lines.append(f"  [ts: {msg['ts']}]")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Read Slack conversation history')
    parser.add_argument(
        '--channel',
        required=True,
        help='Channel or DM ID (e.g., C1234567890)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Maximum messages to return (default: 20)'
    )
    parser.add_argument(
        '--thread',
        help='Thread timestamp to read replies (e.g., 1234567890.123456)'
    )
    parser.add_argument(
        '--show-ids',
        action='store_true',
        help='Show message timestamps (useful for threads)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    client = SlackClient()

    # Get channel info
    channel_info = client.get_channel_info(args.channel)
    channel_name = channel_info['name'] if channel_info else args.channel

    if args.thread:
        # Get thread replies
        messages = client.get_thread_replies(
            channel_id=args.channel,
            thread_ts=args.thread,
            limit=args.limit
        )
        context = f"Thread in #{channel_name}"
    else:
        # Get conversation history
        messages = client.get_conversation_history(
            channel_id=args.channel,
            limit=args.limit
        )
        context = f"#{channel_name}"

    if args.json:
        output = {
            'channel': channel_name,
            'channel_id': args.channel,
            'thread_ts': args.thread,
            'message_count': len(messages),
            'messages': messages
        }
        print(json.dumps(output, indent=2))
        return

    # Pretty print
    print(f"=== {context} ({len(messages)} messages) ===\n")

    for msg in messages:
        print(format_message(msg, show_id=args.show_ids))
        print()

    if not messages:
        print("No messages found.")
        if not args.thread:
            print("Make sure the bot has been invited to this channel.")


if __name__ == '__main__':
    main()
