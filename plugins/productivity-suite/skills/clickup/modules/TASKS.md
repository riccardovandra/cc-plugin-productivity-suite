# Task Operations

List tasks with filters and view task details.

## List Tasks

### Script Usage
```bash
# By space
uv run scripts/list_tasks.py --space "Client Work"

# By folder
uv run scripts/list_tasks.py --folder "Project X"

# By list
uv run scripts/list_tasks.py --list "Sprint 1"

# With status filter
uv run scripts/list_tasks.py --space "Client Work" --status "in progress"

# Include closed tasks
uv run scripts/list_tasks.py --space "Client Work" --include-closed

# Limit results
uv run scripts/list_tasks.py --space "Client Work" --limit 10

# JSON output
uv run scripts/list_tasks.py --space "Client Work" --json
```

### Output Format
```
Found 15 task(s):

**Homepage Redesign**
  Status: in progress
  Assignees: john, sarah
  Due: 2025-01-15
  Priority: high
  List: Sprint 1
  ID: abc123
  URL: https://app.clickup.com/t/abc123

**API Integration**
  Status: open
  Due: 2025-01-20
  List: Backlog
  ID: def456
  URL: https://app.clickup.com/t/def456
```

## Get Task Details

### Script Usage
```bash
# By task ID
uv run scripts/task.py abc123

# Search by name
uv run scripts/task.py --search "homepage"

# Search within a space
uv run scripts/task.py --search "api" --space "Engineering"

# JSON output
uv run scripts/task.py abc123 --json
```

### Output Format
```
# Homepage Redesign

**Status:** in progress
**Assignees:** john, sarah
**Due Date:** 2025-01-15
**Priority:** high
**Tags:** frontend, urgent
**List:** Sprint 1

**URL:** https://app.clickup.com/t/abc123
**ID:** abc123

## Description

Complete the homepage redesign with new hero section and updated navigation.
```

## Conversational Examples

| User Says | Action |
|-----------|--------|
| "Show tasks in Client Work" | `list_tasks.py --space "Client Work"` |
| "What's in progress?" | `list_tasks.py --space "..." --status "in progress"` |
| "Find the homepage task" | `task.py --search "homepage"` |
| "What's the status of API integration?" | `task.py --search "API integration"` |

## Tips

- Must provide at least one filter: `--space`, `--folder`, or `--list`
- Status names are case-insensitive
- Search returns multiple matches if ambiguous - use task ID for exact match
- Use `--space` with `--search` to narrow down results in large workspaces
