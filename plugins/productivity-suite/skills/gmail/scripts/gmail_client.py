#!/usr/bin/env python3
"""
Gmail API Client

Core API wrapper for Gmail operations.
Used by other scripts in this skill.

Usage:
    from gmail_client import GmailClient

    client = GmailClient()
    messages = client.search("from:client@example.com is:unread")
    thread = client.get_thread(thread_id)
"""

import base64
import mimetypes
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

try:
    from googleapiclient.discovery import build
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install google-api-python-client")
    sys.exit(1)

try:
    import markdown
except ImportError:
    print("Missing markdown library. Install with:")
    print("  pip install markdown")
    sys.exit(1)


def _markdown_to_html(text: str) -> str:
    """Convert markdown to HTML with tables and line break support."""
    return markdown.markdown(text, extensions=['tables', 'nl2br'])

# Add integrations to path for shared auth
SKILL_DIR = Path(__file__).parent.parent
INTEGRATIONS_DIR = SKILL_DIR.parent.parent / 'integrations/google/scripts'
sys.path.insert(0, str(INTEGRATIONS_DIR))

from google_auth import get_gmail_credentials


class GmailClient:
    """Gmail API client wrapper."""

    def __init__(self, include_send_scope: bool = False):
        """
        Initialize Gmail client.

        Args:
            include_send_scope: If True, request gmail.send scope
        """
        credentials = get_gmail_credentials(send=include_send_scope)
        self.service = build('gmail', 'v1', credentials=credentials)
        self.user_id = 'me'

    # =========================================================================
    # Search & List
    # =========================================================================

    def search(
        self,
        query: str = '',
        max_results: int = 20,
        label_ids: list[str] = None
    ) -> list[dict]:
        """
        Search for messages.

        Args:
            query: Gmail search query (e.g., "from:x is:unread")
            max_results: Maximum messages to return
            label_ids: Filter by labels (e.g., ['INBOX', 'UNREAD'])

        Returns:
            List of message dicts with id, threadId, snippet, etc.
        """
        params = {
            'userId': self.user_id,
            'maxResults': max_results,
        }
        if query:
            params['q'] = query
        if label_ids:
            params['labelIds'] = label_ids

        results = self.service.users().messages().list(**params).execute()
        messages = results.get('messages', [])

        # Fetch details for each message
        detailed = []
        for msg in messages:
            details = self.get_message(msg['id'], format='metadata')
            if details:
                detailed.append(details)

        return detailed

    def list_labels(self) -> list[dict]:
        """Get all labels in the mailbox."""
        results = self.service.users().labels().list(userId=self.user_id).execute()
        return results.get('labels', [])

    # =========================================================================
    # Read Messages & Threads
    # =========================================================================

    def get_message(
        self,
        message_id: str,
        format: str = 'full'
    ) -> Optional[dict]:
        """
        Get a single message.

        Args:
            message_id: Message ID
            format: 'minimal', 'metadata', 'full', or 'raw'

        Returns:
            Message dict with headers, body, etc.
        """
        try:
            msg = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format=format
            ).execute()
            return self._parse_message(msg)
        except Exception as e:
            print(f"Error getting message {message_id}: {e}", file=sys.stderr)
            return None

    def get_thread(self, thread_id: str) -> Optional[dict]:
        """
        Get a full conversation thread.

        Args:
            thread_id: Thread ID

        Returns:
            Thread dict with all messages
        """
        try:
            thread = self.service.users().threads().get(
                userId=self.user_id,
                id=thread_id,
                format='full'
            ).execute()

            # Parse each message in thread
            messages = []
            for msg in thread.get('messages', []):
                parsed = self._parse_message(msg)
                if parsed:
                    messages.append(parsed)

            return {
                'id': thread['id'],
                'messages': messages,
                'message_count': len(messages)
            }
        except Exception as e:
            print(f"Error getting thread {thread_id}: {e}", file=sys.stderr)
            return None

    def _parse_message(self, msg: dict) -> dict:
        """Parse raw message into structured format."""
        headers = {}
        for header in msg.get('payload', {}).get('headers', []):
            name = header['name'].lower()
            if name in ['from', 'to', 'subject', 'date', 'cc', 'bcc']:
                headers[name] = header['value']

        # Get body
        body = self._extract_body(msg.get('payload', {}))

        # Parse date
        internal_date = msg.get('internalDate')
        if internal_date:
            dt = datetime.fromtimestamp(int(internal_date) / 1000)
            date_str = dt.strftime('%Y-%m-%d %H:%M')
        else:
            date_str = headers.get('date', '')

        return {
            'id': msg['id'],
            'thread_id': msg['threadId'],
            'labels': msg.get('labelIds', []),
            'snippet': msg.get('snippet', ''),
            'from': headers.get('from', ''),
            'to': headers.get('to', ''),
            'cc': headers.get('cc', ''),
            'subject': headers.get('subject', ''),
            'date': date_str,
            'body': body
        }

    def _extract_body(self, payload: dict) -> str:
        """Extract body text from message payload."""
        body = ''

        # Direct body
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        # Multipart
        elif 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')

                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
                elif mime_type == 'text/html' and not body and part.get('body', {}).get('data'):
                    # Fallback to HTML if no plain text
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    # Nested multipart
                    nested = self._extract_body(part)
                    if nested:
                        body = nested
                        break

        return body

    # =========================================================================
    # Modify Messages (Archive, Snooze, Label)
    # =========================================================================

    def archive(self, message_id: str) -> bool:
        """
        Archive a message (remove from inbox).

        Args:
            message_id: Message ID to archive

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error archiving {message_id}: {e}", file=sys.stderr)
            return False

    def archive_thread(self, thread_id: str) -> bool:
        """Archive all messages in a thread."""
        try:
            self.service.users().threads().modify(
                userId=self.user_id,
                id=thread_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error archiving thread {thread_id}: {e}", file=sys.stderr)
            return False

    def mark_thread_read(self, thread_id: str) -> bool:
        """Mark all messages in a thread as read."""
        try:
            self.service.users().threads().modify(
                userId=self.user_id,
                id=thread_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error marking thread as read {thread_id}: {e}", file=sys.stderr)
            return False

    def snooze(self, message_id: str, until: datetime) -> bool:
        """
        Snooze a message until specified time.

        Note: Gmail API doesn't have native snooze. This archives and creates
        a reminder. For true snooze, use Gmail web interface.

        Args:
            message_id: Message ID
            until: When to resurface the message

        Returns:
            True if archived (snooze is simulated)
        """
        # Gmail API doesn't support native snooze
        # Best we can do is archive and note the time
        print(f"Note: True snooze not available via API. Message archived.", file=sys.stderr)
        print(f"Reminder: Check back at {until.strftime('%Y-%m-%d %H:%M')}", file=sys.stderr)
        return self.archive(message_id)

    def add_label(self, message_id: str, label_name: str) -> bool:
        """
        Add a label to a message.

        Args:
            message_id: Message ID
            label_name: Label name (will be created if doesn't exist)

        Returns:
            True if successful
        """
        # Get or create label
        label_id = self._get_or_create_label(label_name)
        if not label_id:
            return False

        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error adding label: {e}", file=sys.stderr)
            return False

    def remove_label(self, message_id: str, label_name: str) -> bool:
        """Remove a label from a message."""
        labels = self.list_labels()
        label_id = None
        for label in labels:
            if label['name'].lower() == label_name.lower():
                label_id = label['id']
                break

        if not label_id:
            print(f"Label not found: {label_name}", file=sys.stderr)
            return False

        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'removeLabelIds': [label_id]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error removing label: {e}", file=sys.stderr)
            return False

    def _get_or_create_label(self, name: str) -> Optional[str]:
        """Get label ID, creating if necessary."""
        labels = self.list_labels()

        for label in labels:
            if label['name'].lower() == name.lower():
                return label['id']

        # Create new label
        try:
            result = self.service.users().labels().create(
                userId=self.user_id,
                body={'name': name}
            ).execute()
            return result['id']
        except Exception as e:
            print(f"Error creating label: {e}", file=sys.stderr)
            return None

    # =========================================================================
    # Drafts (NO SEND)
    # =========================================================================

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = None,
        bcc: str = None,
        thread_id: str = None,
        attachments: list = None
    ) -> Optional[dict]:
        """
        Create a draft email (does NOT send).

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients
            bcc: BCC recipients
            thread_id: Thread ID for replies
            attachments: List of file paths to attach

        Returns:
            Draft dict with id
        """
        html_body = _markdown_to_html(body)

        if attachments:
            # Use multipart message for attachments
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            # Attach the HTML body
            message.attach(MIMEText(html_body, 'html'))

            # Attach files
            for file_path in attachments:
                file_path = Path(file_path)
                if not file_path.exists():
                    print(f"Warning: Attachment not found: {file_path}", file=sys.stderr)
                    continue

                # Guess the content type
                content_type, encoding = mimetypes.guess_type(str(file_path))
                if content_type is None:
                    content_type = 'application/octet-stream'

                main_type, sub_type = content_type.split('/', 1)

                with open(file_path, 'rb') as f:
                    attachment = MIMEBase(main_type, sub_type)
                    attachment.set_payload(f.read())

                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=file_path.name
                )
                message.attach(attachment)
        else:
            # Simple message without attachments
            message = MIMEText(html_body, 'html')
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body = {'message': {'raw': raw}}
        if thread_id:
            draft_body['message']['threadId'] = thread_id

        try:
            draft = self.service.users().drafts().create(
                userId=self.user_id,
                body=draft_body
            ).execute()
            return {
                'id': draft['id'],
                'message_id': draft['message']['id'],
                'thread_id': thread_id
            }
        except Exception as e:
            print(f"Error creating draft: {e}", file=sys.stderr)
            return None

    def list_drafts(self, max_results: int = 10) -> list[dict]:
        """List existing drafts."""
        try:
            results = self.service.users().drafts().list(
                userId=self.user_id,
                maxResults=max_results
            ).execute()
            return results.get('drafts', [])
        except Exception as e:
            print(f"Error listing drafts: {e}", file=sys.stderr)
            return []

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft."""
        try:
            self.service.users().drafts().delete(
                userId=self.user_id,
                id=draft_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error deleting draft: {e}", file=sys.stderr)
            return False


if __name__ == '__main__':
    # Quick test
    print("Gmail Client - Testing connection...")
    client = GmailClient()

    labels = client.list_labels()
    print(f"Found {len(labels)} labels")

    print("\nRecent messages:")
    messages = client.search(max_results=5)
    for msg in messages:
        print(f"  - {msg['from'][:40]}: {msg['subject'][:50]}")
