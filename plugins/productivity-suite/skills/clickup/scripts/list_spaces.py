#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
List spaces in ClickUp workspace.

Usage:
    python list_spaces.py              # All spaces
    python list_spaces.py --with-folders   # Include folders
    python list_spaces.py --json           # JSON output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clickup_client import ClickUpClient


def main():
    parser = argparse.ArgumentParser(description="List ClickUp spaces")
    parser.add_argument("--with-folders", action="store_true", help="Show folders in each space")
    parser.add_argument("--with-lists", action="store_true", help="Show lists in each space/folder")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        client = ClickUpClient()
        spaces = client.list_spaces()

        if args.json:
            output = []
            for space in spaces:
                space_data = client.format_space_summary(space)
                if args.with_folders or args.with_lists:
                    folders = client.list_folders(space["id"])
                    space_data["folders"] = []
                    for f in folders:
                        folder_data = {"id": f["id"], "name": f["name"]}
                        if args.with_lists:
                            lists = client.list_lists_in_folder(f["id"])
                            folder_data["lists"] = [{"id": l["id"], "name": l["name"]} for l in lists]
                        space_data["folders"].append(folder_data)
                    if args.with_lists:
                        folderless = client.list_lists_in_space(space["id"])
                        space_data["folderless_lists"] = [{"id": l["id"], "name": l["name"]} for l in folderless]
                output.append(space_data)
            print(json.dumps(output, indent=2))
        else:
            print(f"Found {len(spaces)} space(s):\n")
            for space in spaces:
                summary = client.format_space_summary(space)
                private_badge = " (private)" if summary["private"] else ""
                print(f"**{summary['name']}**{private_badge}")
                print(f"  ID: {summary['id']}")
                if summary["statuses"]:
                    print(f"  Statuses: {', '.join(summary['statuses'])}")

                if args.with_folders or args.with_lists:
                    folders = client.list_folders(space["id"])
                    if folders:
                        print("  Folders:")
                        for folder in folders:
                            print(f"    - {folder['name']} (ID: {folder['id']})")
                            if args.with_lists:
                                lists = client.list_lists_in_folder(folder["id"])
                                for lst in lists:
                                    print(f"        - {lst['name']} (ID: {lst['id']})")

                    if args.with_lists:
                        folderless = client.list_lists_in_space(space["id"])
                        if folderless:
                            print("  Lists (no folder):")
                            for lst in folderless:
                                print(f"    - {lst['name']} (ID: {lst['id']})")
                print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
