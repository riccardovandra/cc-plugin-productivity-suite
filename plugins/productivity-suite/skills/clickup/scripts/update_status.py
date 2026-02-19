#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
Update task status in ClickUp.

Usage:
    python update_status.py abc123 --status "complete"
    python update_status.py abc123 --complete
    python update_status.py --search "homepage" --status "in progress"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clickup_client import ClickUpClient


def main():
    parser = argparse.ArgumentParser(description="Update ClickUp task status")
    parser.add_argument("task_id", nargs="?", help="Task ID")
    parser.add_argument("--search", help="Search for task by name")
    parser.add_argument("--status", help="New status name")
    parser.add_argument("--complete", action="store_true", help="Mark task as complete")

    args = parser.parse_args()

    if not args.task_id and not args.search:
        parser.error("Must provide task_id or --search")

    if not args.status and not args.complete:
        parser.error("Must provide --status or --complete")

    try:
        client = ClickUpClient()
        task = None
        task_id = args.task_id

        if args.search and not task_id:
            tasks = client.search_tasks(args.search)

            if not tasks:
                print(f"No tasks found matching '{args.search}'")
                sys.exit(1)

            if len(tasks) > 1:
                print(f"Multiple tasks found matching '{args.search}':\n")
                for t in tasks[:10]:
                    summary = client.extract_task_summary(t)
                    print(f"  - {summary['name']} (ID: {summary['id']}) - {summary['status']}")
                print(f"\nUse task ID for exact match")
                sys.exit(1)

            task = tasks[0]
            task_id = task["id"]

        # Determine new status
        new_status = args.status if args.status else "complete"

        # Get current task info
        if not task:
            task = client.get_task(task_id)

        if not task:
            print(f"Task '{task_id}' not found", file=sys.stderr)
            sys.exit(1)

        summary = client.extract_task_summary(task)
        old_status = summary["status"]

        print(f"Updating task: {summary['name']}")
        print(f"  {old_status} -> {new_status}")

        # Update the status
        client.update_task_status(task_id, new_status)

        print(f"\nDone! Task status updated.")
        print(f"View in ClickUp: {summary['url']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
