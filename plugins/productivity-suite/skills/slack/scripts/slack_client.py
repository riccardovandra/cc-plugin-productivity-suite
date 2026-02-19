#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["slack-sdk>=3.27.0"]
# ///
"""
Slack API Client

Core API wrapper for Slack operations.
Used by other scripts in this skill.

Usage:
    from slack_client import SlackClient

    client = SlackClient()
    channels = client.list_channels()
    messages = client.get_conversation_history(channel_id)
"""

import os
import sys
from datetime import datetime
from typing import Optional


def get_client():
    """Get Slack WebClient with bot token."""
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    token = os.getenv('SLACK_BOT_TOKEN')
    if not token:
        print("Error: SLACK_BOT_TOKEN environment variable not set", file=sys.stderr)
        print("\nTo set up:")
        print("1. Create a Slack App at https://api.slack.com/apps")
        print("2. Add required Bot Token Scopes")
        print("3. Install to workspace")
        print("4. Copy Bot User OAuth Token")
        print("5. export SLACK_BOT_TOKEN='xoxb-...'")
        sys.exit(1)

    return WebClient(token=token)


class SlackClient:
    """Slack API client wrapper."""

    def __init__(self):
        """Initialize Slack client."""
        self.client = get_client()
        self._users_cache = {}

    # =========================================================================
    # List Channels & Conversations
    # =========================================================================

    def list_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 100
    ) -> list[dict]:
        """
        List channels in the workspace.

        Args:
            types: Comma-separated list of channel types
                   Options: public_channel, private_channel, mpim, im
            limit: Maximum channels to return

        Returns:
            List of channel dicts with id, name, is_private, etc.
        """
        try:
            result = self.client.conversations_list(
                types=types,
                limit=limit,
                exclude_archived=True
            )

            channels = []
            for channel in result.get('channels', []):
                channels.append({
                    'id': channel['id'],
                    'name': channel.get('name', channel.get('user', 'DM')),
                    'is_private': channel.get('is_private', False),
                    'is_im': channel.get('is_im', False),
                    'is_mpim': channel.get('is_mpim', False),
                    'num_members': channel.get('num_members', 0),
                    'topic': channel.get('topic', {}).get('value', ''),
                    'purpose': channel.get('purpose', {}).get('value', '')
                })

            return channels

        except Exception as e:
            print(f"Error listing channels: {e}", file=sys.stderr)
            return []

    def list_dms(self, limit: int = 50) -> list[dict]:
        """
        List direct message conversations.

        Args:
            limit: Maximum DMs to return

        Returns:
            List of DM dicts with id, user info
        """
        try:
            result = self.client.conversations_list(
                types="im",
                limit=limit
            )

            dms = []
            for dm in result.get('channels', []):
                user_id = dm.get('user')
                user_name = self._get_user_name(user_id) if user_id else 'Unknown'

                dms.append({
                    'id': dm['id'],
                    'user_id': user_id,
                    'user_name': user_name,
                    'is_im': True
                })

            return dms

        except Exception as e:
            print(f"Error listing DMs: {e}", file=sys.stderr)
            return []

    # =========================================================================
    # Read Conversations
    # =========================================================================

    def get_conversation_history(
        self,
        channel_id: str,
        limit: int = 20,
        oldest: str = None,
        latest: str = None
    ) -> list[dict]:
        """
        Get message history from a channel or DM.

        Args:
            channel_id: Channel or DM ID
            limit: Maximum messages to return
            oldest: Start of time range (Unix timestamp)
            latest: End of time range (Unix timestamp)

        Returns:
            List of message dicts with text, user, timestamp, etc.
        """
        try:
            params = {
                'channel': channel_id,
                'limit': limit
            }
            if oldest:
                params['oldest'] = oldest
            if latest:
                params['latest'] = latest

            result = self.client.conversations_history(**params)

            messages = []
            for msg in result.get('messages', []):
                user_id = msg.get('user')
                user_name = self._get_user_name(user_id) if user_id else 'Bot/System'

                # Parse timestamp
                ts = msg.get('ts', '')
                if ts:
                    dt = datetime.fromtimestamp(float(ts))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    date_str = ''

                messages.append({
                    'ts': ts,
                    'date': date_str,
                    'user_id': user_id,
                    'user_name': user_name,
                    'text': msg.get('text', ''),
                    'thread_ts': msg.get('thread_ts'),
                    'reply_count': msg.get('reply_count', 0),
                    'reactions': self._parse_reactions(msg.get('reactions', []))
                })

            # Reverse to show oldest first
            messages.reverse()
            return messages

        except Exception as e:
            print(f"Error getting conversation history: {e}", file=sys.stderr)
            return []

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 50
    ) -> list[dict]:
        """
        Get replies in a thread.

        Args:
            channel_id: Channel ID
            thread_ts: Parent message timestamp
            limit: Maximum replies to return

        Returns:
            List of reply message dicts
        """
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=limit
            )

            messages = []
            for msg in result.get('messages', []):
                user_id = msg.get('user')
                user_name = self._get_user_name(user_id) if user_id else 'Bot/System'

                ts = msg.get('ts', '')
                if ts:
                    dt = datetime.fromtimestamp(float(ts))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    date_str = ''

                messages.append({
                    'ts': ts,
                    'date': date_str,
                    'user_id': user_id,
                    'user_name': user_name,
                    'text': msg.get('text', ''),
                    'is_parent': msg.get('ts') == thread_ts
                })

            return messages

        except Exception as e:
            print(f"Error getting thread replies: {e}", file=sys.stderr)
            return []

    # =========================================================================
    # User Info
    # =========================================================================

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """
        Get user information.

        Args:
            user_id: User ID

        Returns:
            User dict with name, real_name, email, etc.
        """
        try:
            result = self.client.users_info(user=user_id)
            user = result.get('user', {})

            return {
                'id': user['id'],
                'name': user.get('name', ''),
                'real_name': user.get('real_name', ''),
                'display_name': user.get('profile', {}).get('display_name', ''),
                'email': user.get('profile', {}).get('email', ''),
                'is_bot': user.get('is_bot', False)
            }

        except Exception as e:
            print(f"Error getting user info: {e}", file=sys.stderr)
            return None

    def _get_user_name(self, user_id: str) -> str:
        """Get user display name with caching."""
        if user_id in self._users_cache:
            return self._users_cache[user_id]

        user = self.get_user_info(user_id)
        if user:
            name = user.get('display_name') or user.get('real_name') or user.get('name', 'Unknown')
            self._users_cache[user_id] = name
            return name

        return 'Unknown'

    def _parse_reactions(self, reactions: list) -> list[dict]:
        """Parse reaction data."""
        return [
            {
                'name': r.get('name', ''),
                'count': r.get('count', 0)
            }
            for r in reactions
        ]

    # =========================================================================
    # Channel Info
    # =========================================================================

    def get_channel_info(self, channel_id: str) -> Optional[dict]:
        """
        Get channel information.

        Args:
            channel_id: Channel ID

        Returns:
            Channel dict with name, topic, purpose, etc.
        """
        try:
            result = self.client.conversations_info(channel=channel_id)
            channel = result.get('channel', {})

            return {
                'id': channel['id'],
                'name': channel.get('name', ''),
                'is_private': channel.get('is_private', False),
                'is_archived': channel.get('is_archived', False),
                'topic': channel.get('topic', {}).get('value', ''),
                'purpose': channel.get('purpose', {}).get('value', ''),
                'num_members': channel.get('num_members', 0),
                'created': channel.get('created', 0)
            }

        except Exception as e:
            print(f"Error getting channel info: {e}", file=sys.stderr)
            return None


if __name__ == '__main__':
    # Quick test
    print("Slack Client - Testing connection...")
    client = SlackClient()

    channels = client.list_channels()
    print(f"Found {len(channels)} channels")

    if channels:
        print("\nChannels:")
        for ch in channels[:5]:
            prefix = "#" if not ch['is_private'] else "🔒"
            print(f"  {prefix}{ch['name']} ({ch['id']})")
