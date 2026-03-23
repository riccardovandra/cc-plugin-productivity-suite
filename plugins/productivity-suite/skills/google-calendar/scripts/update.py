#!/usr/bin/env python3
"""
Update Calendar Event

Usage:
    python update.py --id EVENT_ID --start "2025-12-30 14:00"
    python update.py --id EVENT_ID --start "tomorrow 3pm" --duration 30
    python update.py --id EVENT_ID --description "Updated description"
    python update.py --id EVENT_ID --start "2025-12-30 10:00" --description "New time and desc"
"""

import argparse
import sys
from datetime import datetime, timedelta

try:
    from dateutil import parser as dateparser
except ImportError:
    print("Missing python-dateutil. Install with:")
    print("  pip install python-dateutil")
    sys.exit(1)

from calendar_client import CalendarClient


def parse_datetime(date_string: str) -> datetime:
    """Parse flexible date/time string."""
    now = datetime.now()

    lower = date_string.lower()
    if lower.startswith('tomorrow'):
        tomorrow = now + timedelta(days=1)
        date_string = date_string.lower().replace('tomorrow', tomorrow.strftime('%Y-%m-%d'))
    elif lower.startswith('today'):
        date_string = date_string.lower().replace('today', now.strftime('%Y-%m-%d'))

    return dateparser.parse(date_string, fuzzy=True)


def main():
    parser = argparse.ArgumentParser(description="Update calendar event")
    parser.add_argument('--id', '-i', required=True, help="Event ID to update")
    parser.add_argument('--start', '-s', help="New start time (e.g., '2025-12-30 14:00', 'tomorrow 3pm')")
    parser.add_argument('--end', '-e', help="New end time")
    parser.add_argument('--duration', '-d', type=int, help="Duration in minutes from new start (requires --start)")
    parser.add_argument('--description', help="New event description")
    parser.add_argument('--json', action='store_true', help="Output as JSON")

    args = parser.parse_args()

    if not any([args.start, args.end, args.description]):
        print("Error: Provide at least one field to update (--start, --end, or --description)", file=sys.stderr)
        sys.exit(1)

    if args.duration and not args.start:
        print("Error: --duration requires --start", file=sys.stderr)
        sys.exit(1)

    start = None
    end = None

    try:
        if args.start:
            start = parse_datetime(args.start)
            if args.duration:
                end = start + timedelta(minutes=args.duration)
        if args.end:
            end = parse_datetime(args.end)
    except Exception as e:
        print(f"Error parsing date: {e}", file=sys.stderr)
        print("Try formats like: '2025-12-30 14:00', 'tomorrow 3pm', 'Dec 25 10:00'")
        sys.exit(1)

    try:
        client = CalendarClient()
        event = client.update_event(
            event_id=args.id,
            start=start,
            end=end,
            description=args.description
        )
    except Exception as e:
        print(f"Error updating event: {e}", file=sys.stderr)
        sys.exit(1)

    if event:
        if args.json:
            import json
            print(json.dumps(event, indent=2))
        else:
            print(f"\nUpdated: {event['title']}")
            print(f"  Start: {event['start']}")
            print(f"  End:   {event['end']}")
            if event.get('description'):
                desc = event['description']
                print(f"  Desc:  {desc[:50]}{'...' if len(desc) > 50 else ''}")
            if event.get('link'):
                print(f"  Link:  {event['link']}")
            print()
    else:
        print("Failed to update event.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
