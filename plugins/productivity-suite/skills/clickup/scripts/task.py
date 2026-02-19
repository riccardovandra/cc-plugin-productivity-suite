#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
Get task details from ClickUp.

Usage:
    python task.py abc123              # By task ID
    python task.py --search "homepage"  # Search by name
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clickup_client import ClickUpClient


def format_task_detail(summary: dict, description: str = "") -> str:
    """Format full task details for display."""
    lines = [f"# {summary['name']}\n"]
    lines.append(f"**Status:** {summary['status']}")

    if summary['assignees']:
        lines.append(f"**Assignees:** {', '.join(summary['assignees'])}")
    if summary['due_date']:
        lines.append(f"**Due Date:** {summary['due_date']}")
    if summary['start_date']:
        lines.append(f"**Start Date:** {summary['start_date']}")
    if summary['priority']:
        lines.append(f"**Priority:** {summary['priority']}")
    if summary['tags']:
        lines.append(f"**Tags:** {', '.join(summary['tags'])}")
    if summary['list_name']:
        lines.append(f"**List:** {summary['list_name']}")

    lines.append(f"\n**URL:** {summary['url']}")
    lines.append(f"**ID:** {summary['id']}")

    if description:
        lines.append(f"\n## Description\n\n{description}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Get ClickUp task details")
    parser.add_argument("task_id", nargs="?", help="Task ID")
    parser.add_argument("--search", help="Search for task by name")
    parser.add_argument("--space", help="Limit search to space (for --search)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.task_id and not args.search:
        parser.error("Must provide task_id or --search")

    try:
        client = ClickUpClient()
        task = None

        if args.task_id:
            task = client.get_task(args.task_id)
            if not task:
                print(f"Task '{args.task_id}' not found", file=sys.stderr)
                sys.exit(1)
        else:
            # Search for task
            space_id = None
            if args.space:
                space = client.find_space_by_name(args.space)
                if space:
                    space_id = space["id"]

            tasks = client.search_tasks(args.search, space_id=space_id)

            if not tasks:
                print(f"No tasks found matching '{args.search}'")
                sys.exit(1)

            if len(tasks) > 1:
                print(f"Multiple tasks found matching '{args.search}':\n")
                for t in tasks[:10]:
                    summary = client.extract_task_summary(t)
                    print(f"  - {summary['name']} (ID: {summary['id']}) - {summary['status']}")
                print(f"\nUse task ID for exact match: uv run scripts/task.py <id>")
                sys.exit(0)

            task = tasks[0]

        summary = client.extract_task_summary(task)

        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(format_task_detail(summary, task.get("description", "")))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
