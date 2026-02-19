#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["slack-sdk>=3.27.0"]
# ///
"""
Create Slack Draft Messages

Creates draft messages saved locally (does NOT send to Slack).
User must manually copy and send.

Usage:
    uv run draft.py --channel C1234567890 --message "Hello team!"
    uv run draft.py --channel C1234567890 --file message.txt
    uv run draft.py --channel C1234567890 --message "Reply" --thread 1234567890.123456
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent for slack_client
sys.path.insert(0, str(Path(__file__).parent))
from slack_client import SlackClient


def save_draft(
    channel_name: str,
    channel_id: str,
    message: str,
    thread_ts: str = None,
    output_dir: Path = None
) -> Path:
    """
    Save draft message to local file.

    Returns path to saved draft.
    """
    if output_dir is None:
        # Default output location
        today = datetime.now().strftime('%Y-%m-%d')
        workspace = Path(__file__).parent.parent.parent.parent.parent / 'workspace'
        output_dir = workspace / 'docs' / f'{today} - Slack Drafts'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime('%H%M%S')
    safe_name = channel_name.replace('#', '').replace(' ', '-')[:30]
    filename = f"draft-{safe_name}-{timestamp}.md"

    draft_path = output_dir / filename

    # Build draft content
    content_lines = [
        f"# Slack Draft Message",
        "",
        f"**Channel:** #{channel_name}",
        f"**Channel ID:** `{channel_id}`",
        f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if thread_ts:
        content_lines.append(f"**Thread:** `{thread_ts}` (reply)")

    content_lines.extend([
        "",
        "---",
        "",
        "## Message",
        "",
        message,
        "",
        "---",
        "",
        "## How to Send",
        "",
        "1. Open Slack",
        f"2. Go to #{channel_name}",
    ])

    if thread_ts:
        content_lines.append(f"3. Find the thread with timestamp `{thread_ts}`")
        content_lines.append("4. Paste the message above and send")
    else:
        content_lines.append("3. Paste the message above and send")

    draft_path.write_text('\n'.join(content_lines))
    return draft_path


def main():
    parser = argparse.ArgumentParser(description='Create Slack draft message (does NOT send)')
    parser.add_argument(
        '--channel',
        required=True,
        help='Channel or DM ID (e.g., C1234567890)'
    )
    parser.add_argument(
        '--message',
        help='Message text (or use --file)'
    )
    parser.add_argument(
        '--file',
        type=Path,
        help='Read message from file'
    )
    parser.add_argument(
        '--thread',
        help='Thread timestamp for reply (e.g., 1234567890.123456)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Directory to save draft (default: workspace/docs/DATE - Slack Drafts/)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    # Get message content
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        message = args.file.read_text()
    elif args.message:
        message = args.message
    else:
        print("Error: Either --message or --file is required", file=sys.stderr)
        sys.exit(1)

    # Get channel info
    client = SlackClient()
    channel_info = client.get_channel_info(args.channel)
    channel_name = channel_info['name'] if channel_info else args.channel

    # Save draft
    draft_path = save_draft(
        channel_name=channel_name,
        channel_id=args.channel,
        message=message,
        thread_ts=args.thread,
        output_dir=args.output_dir
    )

    if args.json:
        output = {
            'status': 'draft_saved',
            'channel': channel_name,
            'channel_id': args.channel,
            'thread_ts': args.thread,
            'draft_path': str(draft_path),
            'message_preview': message[:100] + '...' if len(message) > 100 else message
        }
        print(json.dumps(output, indent=2))
        return

    # Pretty print
    print("=" * 50)
    print("DRAFT SAVED (not sent)")
    print("=" * 50)
    print()
    print(f"Channel: #{channel_name}")
    if args.thread:
        print(f"Thread: {args.thread}")
    print(f"Saved to: {draft_path}")
    print()
    print("--- Message Preview ---")
    print()
    preview = message[:500] + '...' if len(message) > 500 else message
    print(preview)
    print()
    print("--- End Preview ---")
    print()
    print("To send: Open the draft file and follow instructions.")


if __name__ == '__main__':
    main()
