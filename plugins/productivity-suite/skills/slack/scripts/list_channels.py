#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["slack-sdk>=3.27.0"]
# ///
"""
List Slack Channels

Lists channels, DMs, and group conversations.

Usage:
    uv run list_channels.py
    uv run list_channels.py --type public_channel
    uv run list_channels.py --type im  # DMs only
    uv run list_channels.py --include-dms
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent for slack_client
sys.path.insert(0, str(Path(__file__).parent))
from slack_client import SlackClient


def main():
    parser = argparse.ArgumentParser(description='List Slack channels')
    parser.add_argument(
        '--type',
        default='public_channel,private_channel',
        help='Channel types: public_channel, private_channel, mpim, im (comma-separated)'
    )
    parser.add_argument(
        '--include-dms',
        action='store_true',
        help='Include direct messages in listing'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum channels to return (default: 100)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    client = SlackClient()

    # Get channels
    channels = client.list_channels(types=args.type, limit=args.limit)

    # Optionally add DMs
    dms = []
    if args.include_dms and 'im' not in args.type:
        dms = client.list_dms()

    if args.json:
        output = {
            'channels': channels,
            'dms': dms if dms else []
        }
        print(json.dumps(output, indent=2))
        return

    # Pretty print
    if channels:
        print(f"=== Channels ({len(channels)}) ===\n")
        for ch in channels:
            if ch['is_private']:
                prefix = "🔒"
            elif ch['is_mpim']:
                prefix = "👥"
            else:
                prefix = "#"

            name = ch['name']
            members = f"({ch['num_members']} members)" if ch['num_members'] else ""
            topic = f" - {ch['topic'][:50]}..." if ch['topic'] and len(ch['topic']) > 50 else f" - {ch['topic']}" if ch['topic'] else ""

            print(f"{prefix} {name} {members}{topic}")
            print(f"   ID: {ch['id']}")
            print()

    if dms:
        print(f"\n=== Direct Messages ({len(dms)}) ===\n")
        for dm in dms:
            print(f"💬 {dm['user_name']}")
            print(f"   ID: {dm['id']}")
            print()

    if not channels and not dms:
        print("No channels found. Make sure the bot has been added to channels.")


if __name__ == '__main__':
    main()
