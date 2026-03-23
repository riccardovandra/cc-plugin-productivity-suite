#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client", "google-auth-oauthlib", "python-dateutil"]
# ///
"""
View Calendar Events

Usage:
    python today.py                  # Today's events
    python today.py --tomorrow       # Tomorrow's events
    python today.py --week           # This week's events
    python today.py --json           # Output as JSON
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from calendar_client import CalendarClient


def format_time(iso_string: str, all_day: bool = False) -> str:
    """Format ISO time string for display."""
    if all_day:
        return "All day"
    if 'T' in iso_string:
        # Parse and format just the time
        try:
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            return dt.strftime('%H:%M')
        except ValueError:
            return iso_string[11:16]
    return iso_string


def main():
    parser = argparse.ArgumentParser(description="View calendar events")
    parser.add_argument('--tomorrow', action='store_true', help="Show tomorrow's events")
    parser.add_argument('--week', action='store_true', help="Show this week's events")
    parser.add_argument('--json', action='store_true', help="Output as JSON")

    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if args.week:
        time_min = today_start
        time_max = today_start + timedelta(days=7)
        label = "This Week"
    elif args.tomorrow:
        time_min = today_start + timedelta(days=1)
        time_max = time_min + timedelta(days=1)
        label = "Tomorrow"
    else:
        time_min = today_start
        time_max = today_start + timedelta(days=1)
        label = "Today"

    try:
        client = CalendarClient(readonly=True)
        events = client.get_events(time_min=time_min, time_max=time_max)
    except Exception as e:
        print(f"Error fetching events: {e}", file=sys.stderr)
        print("\nIf you haven't set up OAuth yet, run:")
        print("  cd .claude/integrations/google/scripts")
        print("  python oauth_setup.py --add-scope calendar.events")
        sys.exit(1)

    if args.json:
        print(json.dumps({'label': label, 'count': len(events), 'events': events}, indent=2))
    else:
        print(f"\n{label}'s Events ({len(events)}):")
        print("-" * 50)

        if not events:
            print("  No events scheduled.")
        else:
            for event in events:
                time_str = format_time(event['start'], event['all_day'])
                print(f"  {time_str:7}  {event['title']}")
                if event.get('location'):
                    print(f"           @ {event['location']}")
        print()


if __name__ == '__main__':
    main()
