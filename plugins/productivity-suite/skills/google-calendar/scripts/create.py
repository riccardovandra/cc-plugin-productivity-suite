#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client>=2.0.0", "google-auth-oauthlib>=1.0.0", "python-dateutil>=2.8.0"]
# ///
"""
Create Calendar Event

Usage:
    python create.py --title "Meeting" --start "2025-12-21 14:00"
    python create.py --title "Call" --start "2025-12-21 10:00" --duration 30
    python create.py --title "Workshop" --start "2025-12-21 09:00" --end "2025-12-21 12:00"
    python create.py --title "Quick sync" --start "tomorrow 3pm" --duration 15
    python create.py --title "Call" --start "2025-12-21 14:00" --attendee "person@example.com"
    python create.py --title "Video Call" --start "tomorrow 2pm" --meet  # Adds Google Meet link
"""

import argparse
import sys
from datetime import datetime

try:
    from dateutil import parser as dateparser
except ImportError:
    print("Missing python-dateutil. Install with:")
    print("  pip install python-dateutil")
    sys.exit(1)

from calendar_client import CalendarClient


def parse_datetime(date_string: str) -> datetime:
    """Parse flexible date/time string."""
    # Handle relative terms
    now = datetime.now()

    lower = date_string.lower()
    if lower.startswith('tomorrow'):
        # Replace "tomorrow" with actual date
        from datetime import timedelta
        tomorrow = now + timedelta(days=1)
        date_string = date_string.lower().replace('tomorrow', tomorrow.strftime('%Y-%m-%d'))
    elif lower.startswith('today'):
        date_string = date_string.lower().replace('today', now.strftime('%Y-%m-%d'))

    return dateparser.parse(date_string, fuzzy=True)


def main():
    parser = argparse.ArgumentParser(description="Create calendar event")
    parser.add_argument('--title', '-t', required=True, help="Event title")
    parser.add_argument('--start', '-s', required=True, help="Start time (e.g., '2025-12-21 14:00', 'tomorrow 3pm')")
    parser.add_argument('--end', '-e', help="End time (optional, use duration instead)")
    parser.add_argument('--duration', '-d', type=int, default=60, help="Duration in minutes (default: 60)")
    parser.add_argument('--description', help="Event description")
    parser.add_argument('--location', '-l', help="Event location")
    parser.add_argument('--attendee', '-a', action='append', help="Attendee email (can be used multiple times)")
    parser.add_argument('--meet', '-m', action='store_true', help="Add Google Meet video conferencing")
    parser.add_argument('--json', action='store_true', help="Output as JSON")

    args = parser.parse_args()

    try:
        start = parse_datetime(args.start)
        end = parse_datetime(args.end) if args.end else None
    except Exception as e:
        print(f"Error parsing date: {e}", file=sys.stderr)
        print("Try formats like: '2025-12-21 14:00', 'tomorrow 3pm', 'Dec 25 10:00'")
        sys.exit(1)

    try:
        client = CalendarClient()
        event = client.create_event(
            title=args.title,
            start=start,
            end=end,
            duration_minutes=args.duration,
            description=args.description,
            location=args.location,
            attendees=args.attendee,
            add_meet=args.meet
        )
    except Exception as e:
        print(f"Error creating event: {e}", file=sys.stderr)
        print("\nIf you haven't set up OAuth yet, run:")
        print("  cd .claude/integrations/google/scripts")
        print("  python oauth_setup.py --add-scope calendar.events")
        sys.exit(1)

    if event:
        if args.json:
            import json
            print(json.dumps(event, indent=2))
        else:
            print(f"\nCreated: {event['title']}")
            print(f"  Start: {event['start']}")
            print(f"  End:   {event['end']}")
            if event.get('location'):
                print(f"  Where: {event['location']}")
            if event.get('meet_link'):
                print(f"  Meet:  {event['meet_link']}")
            if event.get('link'):
                print(f"  Link:  {event['link']}")
            print()
    else:
        print("Failed to create event.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
