#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
List tasks in ClickUp with filters.

Usage:
    python list_tasks.py --space "Client Work"
    python list_tasks.py --folder "Project X"
    python list_tasks.py --list "Sprint 1"
    python list_tasks.py --space "Client Work" --status "in progress"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clickup_client import ClickUpClient


def format_task(summary: dict) -> str:
    """Format a task summary for display."""
    lines = [f"**{summary['name']}**"]
    lines.append(f"  Status: {summary['status']}")

    if summary['assignees']:
        lines.append(f"  Assignees: {', '.join(summary['assignees'])}")
    if summary['due_date']:
        lines.append(f"  Due: {summary['due_date']}")
    if summary['priority']:
        lines.append(f"  Priority: {summary['priority']}")
    if summary['list_name']:
        lines.append(f"  List: {summary['list_name']}")
    lines.append(f"  ID: {summary['id']}")
    if summary['url']:
        lines.append(f"  URL: {summary['url']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="List ClickUp tasks")
    parser.add_argument("--space", help="Filter by space name")
    parser.add_argument("--folder", help="Filter by folder name")
    parser.add_argument("--list", help="Filter by list name or ID")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--include-closed", action="store_true", help="Include closed tasks")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not any([args.space, args.folder, args.list]):
        parser.error("Must provide at least one filter: --space, --folder, or --list")

    try:
        client = ClickUpClient()
        tasks = []

        space_id = None
        folder_id = None
        list_ids = []

        # Resolve space
        if args.space:
            space = client.find_space_by_name(args.space)
            if not space:
                print(f"Space '{args.space}' not found", file=sys.stderr)
                sys.exit(1)
            space_id = space["id"]

        # Resolve folder
        if args.folder:
            if space_id:
                folder = client.find_folder_by_name(space_id, args.folder)
                if folder:
                    folder_id = folder["id"]
            else:
                result = client.find_folder_across_spaces(args.folder)
                if result:
                    folder, found_space_id = result
                    folder_id = folder["id"]
                    space_id = found_space_id

            if not folder_id:
                print(f"Folder '{args.folder}' not found", file=sys.stderr)
                sys.exit(1)

        # Resolve list
        if args.list:
            lst = client.find_list_by_name(args.list, space_id=space_id, folder_id=folder_id)
            if lst:
                list_ids.append(lst["id"])
            else:
                # Try as list ID directly
                list_ids.append(args.list)
        else:
            # Get all lists in scope
            if folder_id:
                lists = client.list_lists_in_folder(folder_id)
                list_ids = [l["id"] for l in lists]
            elif space_id:
                lists = client.list_lists_in_space(space_id)
                list_ids = [l["id"] for l in lists]
                folders = client.list_folders(space_id)
                for folder in folders:
                    for lst in client.list_lists_in_folder(folder["id"]):
                        list_ids.append(lst["id"])

        # Fetch tasks from all lists
        status_filter = [args.status] if args.status else None

        for list_id in list_ids:
            try:
                list_tasks = client.list_tasks(
                    list_id,
                    statuses=status_filter,
                    include_closed=args.include_closed
                )
                for t in list_tasks:
                    t["_list_id"] = list_id
                tasks.extend(list_tasks)
            except Exception as e:
                print(f"Warning: Could not fetch tasks from list {list_id}: {e}", file=sys.stderr)

            if len(tasks) >= args.limit:
                break

        tasks = tasks[:args.limit]

        if not tasks:
            print("No tasks found matching the criteria.")
            return

        if args.json:
            results = [client.extract_task_summary(t) for t in tasks]
            print(json.dumps(results, indent=2))
        else:
            print(f"Found {len(tasks)} task(s):\n")
            for task in tasks:
                summary = client.extract_task_summary(task)
                print(format_task(summary))
                print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
