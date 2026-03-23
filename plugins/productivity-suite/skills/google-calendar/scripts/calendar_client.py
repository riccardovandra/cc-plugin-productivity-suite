#!/usr/bin/env python3
"""
Google Calendar API Client

Core API wrapper for Calendar operations.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    from googleapiclient.discovery import build
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install google-api-python-client")
    sys.exit(1)

# Add integrations to path for shared auth
SKILL_DIR = Path(__file__).parent.parent
INTEGRATIONS_DIR = SKILL_DIR.parent.parent / 'integrations/google/scripts'
sys.path.insert(0, str(INTEGRATIONS_DIR))

from google_auth import get_calendar_credentials


class CalendarClient:
    """Google Calendar API client wrapper."""

    def __init__(self, readonly: bool = False):
        credentials = get_calendar_credentials(readonly=readonly)
        self.service = build('calendar', 'v3', credentials=credentials)
        self.calendar_id = 'primary'

    def get_events(
        self,
        time_min: datetime = None,
        time_max: datetime = None,
        max_results: int = 50
    ) -> list[dict]:
        """Get events within a time range."""
        now = datetime.now(timezone.utc)

        if time_min is None:
            # Start of today in UTC
            time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_min.tzinfo is None:
            # Assume local time, convert to UTC
            time_min = time_min.replace(tzinfo=timezone.utc)

        if time_max is None:
            time_max = time_min + timedelta(days=1)
        elif time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=timezone.utc)

        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return [self._parse_event(e) for e in events]

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime = None,
        duration_minutes: int = 60,
        description: str = None,
        location: str = None,
        attendees: list[str] = None,
        add_meet: bool = False
    ) -> Optional[dict]:
        """Create a calendar event."""
        if end is None:
            end = start + timedelta(minutes=duration_minutes)

        # Use Europe/Rome timezone for naive datetimes
        default_tz = 'Europe/Rome'

        event_body = {
            'summary': title,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': str(start.tzinfo) if start.tzinfo else default_tz
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': str(end.tzinfo) if end.tzinfo else default_tz
            },
        }

        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
            add_meet = True  # Auto-add Meet when inviting attendees

        if add_meet:
            import uuid
            event_body['conferenceData'] = {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }

        try:
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body,
                sendUpdates='all',
                conferenceDataVersion=1 if add_meet else 0
            ).execute()
            return self._parse_event(event)
        except Exception as e:
            print(f"Error creating event: {e}", file=sys.stderr)
            return None

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error deleting event: {e}", file=sys.stderr)
            return False

    def update_event(
        self,
        event_id: str,
        start: datetime = None,
        end: datetime = None,
        description: str = None
    ) -> Optional[dict]:
        """Update an existing calendar event.

        Only provided fields will be updated; others remain unchanged.
        Uses patch() for partial updates.
        """
        default_tz = 'Europe/Rome'
        body = {}

        # Build update body with only provided fields
        if start is not None:
            body['start'] = {
                'dateTime': start.isoformat(),
                'timeZone': str(start.tzinfo) if start.tzinfo else default_tz
            }
            # If end not provided but start is, we need to set end too
            if end is None:
                # Get current event to preserve duration
                try:
                    current = self.service.events().get(
                        calendarId=self.calendar_id,
                        eventId=event_id
                    ).execute()
                    current_start = current.get('start', {}).get('dateTime')
                    current_end = current.get('end', {}).get('dateTime')
                    if current_start and current_end:
                        from dateutil import parser as dateparser
                        old_start = dateparser.parse(current_start)
                        old_end = dateparser.parse(current_end)
                        duration = old_end - old_start
                        end = start + duration
                except Exception:
                    # Default to 1 hour if we can't get current duration
                    end = start + timedelta(hours=1)

        if end is not None:
            body['end'] = {
                'dateTime': end.isoformat(),
                'timeZone': str(end.tzinfo) if end.tzinfo else default_tz
            }

        if description is not None:
            body['description'] = description

        if not body:
            print("No fields to update", file=sys.stderr)
            return None

        try:
            event = self.service.events().patch(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=body
            ).execute()
            return self._parse_event(event)
        except Exception as e:
            print(f"Error updating event: {e}", file=sys.stderr)
            return None

    def _parse_event(self, event: dict) -> dict:
        """Parse raw event into structured format."""
        start = event.get('start', {})
        end = event.get('end', {})

        # Extract Google Meet link if present
        meet_link = None
        conference_data = event.get('conferenceData', {})
        for entry_point in conference_data.get('entryPoints', []):
            if entry_point.get('entryPointType') == 'video':
                meet_link = entry_point.get('uri')
                break

        return {
            'id': event.get('id'),
            'title': event.get('summary', '(No title)'),
            'start': start.get('dateTime') or start.get('date'),
            'end': end.get('dateTime') or end.get('date'),
            'location': event.get('location'),
            'description': event.get('description'),
            'link': event.get('htmlLink'),
            'meet_link': meet_link,
            'all_day': 'date' in start and 'dateTime' not in start
        }


if __name__ == '__main__':
    # Quick test
    print("Testing Calendar Client...")
    client = CalendarClient(readonly=True)
    events = client.get_events()
    print(f"Found {len(events)} events today")
    for e in events[:3]:
        print(f"  - {e['title']} at {e['start']}")
