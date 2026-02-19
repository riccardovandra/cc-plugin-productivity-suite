#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
ClickUp API Client

Core client for interacting with ClickUp API.
Handles authentication, workspace hierarchy navigation, and task operations.
"""

import os
import sys
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parents[4] / '.env'
load_dotenv(env_path)


class ClickUpClient:
    """Client for ClickUp API operations."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self):
        """Initialize the ClickUp client with API key from environment."""
        self.api_key = os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            raise ValueError("CLICKUP_API_KEY not found in environment variables")

        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

        self._workspace_id: Optional[str] = None

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Make an API request to ClickUp."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json() if response.text else {}

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}", file=sys.stderr)
            print(f"Response: {e.response.text}", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}", file=sys.stderr)
            raise

    # ===== WORKSPACE OPERATIONS =====

    def get_workspace_id(self) -> str:
        """Get the primary workspace (team) ID. Cached after first call."""
        if self._workspace_id:
            return self._workspace_id

        result = self._request("GET", "/team")
        teams = result.get("teams", [])
        if not teams:
            raise ValueError("No workspaces found for this API key")

        self._workspace_id = teams[0]["id"]
        return self._workspace_id

    def get_workspaces(self) -> List[Dict]:
        """Get all workspaces (teams) accessible to the API key."""
        result = self._request("GET", "/team")
        return result.get("teams", [])

    # ===== SPACE OPERATIONS =====

    def list_spaces(self, archived: bool = False) -> List[Dict]:
        """List all spaces in the workspace."""
        workspace_id = self.get_workspace_id()
        params = {"archived": str(archived).lower()}
        result = self._request("GET", f"/team/{workspace_id}/space", params=params)
        return result.get("spaces", [])

    def get_space(self, space_id: str) -> Optional[Dict]:
        """Get a specific space by ID."""
        try:
            return self._request("GET", f"/space/{space_id}")
        except:
            return None

    def find_space_by_name(self, name: str) -> Optional[Dict]:
        """Find a space by name (case-insensitive partial match)."""
        spaces = self.list_spaces()
        name_lower = name.lower()
        for space in spaces:
            if name_lower in space.get("name", "").lower():
                return space
        return None

    # ===== FOLDER OPERATIONS =====

    def list_folders(self, space_id: str, archived: bool = False) -> List[Dict]:
        """List folders in a space."""
        params = {"archived": str(archived).lower()}
        result = self._request("GET", f"/space/{space_id}/folder", params=params)
        return result.get("folders", [])

    def find_folder_by_name(self, space_id: str, name: str) -> Optional[Dict]:
        """Find a folder by name within a space."""
        folders = self.list_folders(space_id)
        name_lower = name.lower()
        for folder in folders:
            if name_lower in folder.get("name", "").lower():
                return folder
        return None

    def find_folder_across_spaces(self, name: str) -> Optional[tuple]:
        """Find a folder by name across all spaces. Returns (folder, space_id)."""
        for space in self.list_spaces():
            folder = self.find_folder_by_name(space["id"], name)
            if folder:
                return folder, space["id"]
        return None

    # ===== LIST OPERATIONS =====

    def list_lists_in_folder(self, folder_id: str, archived: bool = False) -> List[Dict]:
        """List all lists within a folder."""
        params = {"archived": str(archived).lower()}
        result = self._request("GET", f"/folder/{folder_id}/list", params=params)
        return result.get("lists", [])

    def list_lists_in_space(self, space_id: str, archived: bool = False) -> List[Dict]:
        """List folderless lists directly in a space."""
        params = {"archived": str(archived).lower()}
        result = self._request("GET", f"/space/{space_id}/list", params=params)
        return result.get("lists", [])

    def find_list_by_name(self, name: str, space_id: Optional[str] = None, folder_id: Optional[str] = None) -> Optional[Dict]:
        """Find a list by name. Searches within provided scope."""
        lists = []

        if folder_id:
            lists = self.list_lists_in_folder(folder_id)
        elif space_id:
            folders = self.list_folders(space_id)
            for folder in folders:
                lists.extend(self.list_lists_in_folder(folder["id"]))
            lists.extend(self.list_lists_in_space(space_id))
        else:
            for space in self.list_spaces():
                folders = self.list_folders(space["id"])
                for folder in folders:
                    lists.extend(self.list_lists_in_folder(folder["id"]))
                lists.extend(self.list_lists_in_space(space["id"]))

        name_lower = name.lower()
        for lst in lists:
            if name_lower in lst.get("name", "").lower():
                return lst
        return None

    # ===== TASK OPERATIONS =====

    def list_tasks(
        self,
        list_id: str,
        archived: bool = False,
        page: int = 0,
        statuses: Optional[List[str]] = None,
        include_closed: bool = False
    ) -> List[Dict]:
        """List tasks in a list."""
        params = {
            "archived": str(archived).lower(),
            "page": page,
            "include_closed": str(include_closed).lower()
        }

        if statuses:
            params["statuses[]"] = statuses

        result = self._request("GET", f"/list/{list_id}/task", params=params)
        return result.get("tasks", [])

    def get_task(self, task_id: str, include_subtasks: bool = False) -> Optional[Dict]:
        """Get a specific task by ID."""
        params = {"include_subtasks": str(include_subtasks).lower()}
        try:
            return self._request("GET", f"/task/{task_id}", params=params)
        except:
            return None

    def search_tasks(self, query: str, space_id: Optional[str] = None) -> List[Dict]:
        """
        Search tasks by name across workspace or within a space.

        Note: ClickUp lacks a direct search endpoint, so this iterates through lists.
        For better performance, provide a space_id to narrow the search.
        """
        query_lower = query.lower()
        matching_tasks = []

        if space_id:
            spaces = [{"id": space_id, "name": ""}]
            space_obj = self.get_space(space_id)
            if space_obj:
                spaces[0]["name"] = space_obj.get("name", "")
        else:
            spaces = self.list_spaces()

        for space in spaces:
            lists = self.list_lists_in_space(space["id"])

            folders = self.list_folders(space["id"])
            for folder in folders:
                lists.extend(self.list_lists_in_folder(folder["id"]))

            for lst in lists:
                tasks = self.list_tasks(lst["id"], include_closed=True)
                for task in tasks:
                    if query_lower in task.get("name", "").lower():
                        task["_list_name"] = lst.get("name", "")
                        task["_space_name"] = space.get("name", "")
                        matching_tasks.append(task)

        return matching_tasks

    def update_task(self, task_id: str, updates: Dict) -> Dict:
        """Update a task."""
        return self._request("PUT", f"/task/{task_id}", data=updates)

    def update_task_status(self, task_id: str, status: str) -> Dict:
        """Update a task's status."""
        return self.update_task(task_id, {"status": status})

    # ===== COMMENTS OPERATIONS =====

    def get_task_comments(self, task_id: str, start: int = 0) -> List[Dict]:
        """Get comments on a task."""
        params = {}
        if start:
            params["start"] = start

        result = self._request("GET", f"/task/{task_id}/comment", params=params)
        return result.get("comments", [])

    # ===== HELPER METHODS =====

    def extract_task_summary(self, task: Dict) -> Dict:
        """Extract a clean summary from a task record."""
        assignees = task.get("assignees", [])
        assignee_names = [a.get("username", a.get("email", "Unknown")) for a in assignees]

        status = task.get("status", {})
        status_name = status.get("status", "Unknown")
        status_color = status.get("color", "")

        due_date = task.get("due_date")
        if due_date:
            due_date = datetime.fromtimestamp(int(due_date) / 1000).strftime("%Y-%m-%d")

        start_date = task.get("start_date")
        if start_date:
            start_date = datetime.fromtimestamp(int(start_date) / 1000).strftime("%Y-%m-%d")

        priority = task.get("priority")
        priority_name = priority.get("priority", "") if priority else ""

        return {
            "id": task.get("id", ""),
            "name": task.get("name", ""),
            "description": task.get("description", ""),
            "status": status_name,
            "status_color": status_color,
            "assignees": assignee_names,
            "due_date": due_date,
            "start_date": start_date,
            "priority": priority_name,
            "url": task.get("url", ""),
            "list_name": task.get("_list_name", task.get("list", {}).get("name", "")),
            "space_name": task.get("_space_name", ""),
            "tags": [t.get("name", "") for t in task.get("tags", [])]
        }

    def format_space_summary(self, space: Dict) -> Dict:
        """Extract a clean summary from a space record."""
        return {
            "id": space.get("id", ""),
            "name": space.get("name", ""),
            "private": space.get("private", False),
            "statuses": [s.get("status", "") for s in space.get("statuses", [])]
        }

    def format_comment(self, comment: Dict) -> Dict:
        """Extract a clean summary from a comment record."""
        date = comment.get("date")
        if date:
            date = datetime.fromtimestamp(int(date) / 1000).strftime("%Y-%m-%d %H:%M")

        user = comment.get("user", {})

        # Handle comment text - can be in different formats
        comment_text = ""
        if "comment_text" in comment:
            comment_text = comment["comment_text"]
        elif "comment" in comment:
            # Sometimes it's a list of text blocks
            comment_data = comment["comment"]
            if isinstance(comment_data, list):
                comment_text = " ".join([c.get("text", "") for c in comment_data if isinstance(c, dict)])
            else:
                comment_text = str(comment_data)

        return {
            "id": comment.get("id", ""),
            "text": comment_text,
            "user": user.get("username", user.get("email", "Unknown")),
            "date": date
        }


if __name__ == "__main__":
    try:
        client = ClickUpClient()
        print("ClickUp client initialized successfully!")

        print("\nFetching spaces...")
        spaces = client.list_spaces()

        for space in spaces[:5]:
            summary = client.format_space_summary(space)
            print(f"  - {summary['name']} (ID: {summary['id']})")

        print(f"\nTotal spaces: {len(spaces)}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
