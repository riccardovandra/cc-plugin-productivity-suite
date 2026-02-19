# Hierarchy Browsing

Navigate the ClickUp workspace hierarchy: Workspace > Spaces > Folders > Lists > Tasks

## Hierarchy Overview

```
Workspace (Team)
└── Space (e.g., "Client Work", "Internal")
    ├── Folder (optional grouping)
    │   └── List (contains tasks)
    └── List (folderless - directly in space)
```

## Script Usage

### List All Spaces
```bash
uv run scripts/list_spaces.py
uv run scripts/list_spaces.py --with-folders
uv run scripts/list_spaces.py --with-lists
uv run scripts/list_spaces.py --json
```

### Browse Within a Space
```bash
# Show all tasks in a space
uv run scripts/list_tasks.py --space "Client Work"

# Show tasks in a specific folder
uv run scripts/list_tasks.py --folder "Project X"

# Show tasks in a specific list
uv run scripts/list_tasks.py --list "Sprint 1"
```

## Conversational Examples

| User Says | Action |
|-----------|--------|
| "What spaces do I have?" | `list_spaces.py` |
| "Show me the Client Work space" | `list_spaces.py --with-folders`, filter to Client Work |
| "What's in the ProjectX folder?" | `list_tasks.py --folder "ProjectX"` |
| "List all my lists" | `list_spaces.py --with-lists` |

## Output Format

```
Found 3 space(s):

**Client Work**
  ID: abc123
  Statuses: Open, In Progress, Review, Complete
  Folders:
    - Acme Corp (ID: def456)
    - TechStart (ID: ghi789)

**Internal**
  ID: jkl012
  Statuses: To Do, Doing, Done
```

## Tips

- Space and folder names are case-insensitive for searching
- Use `--json` output for programmatic parsing
- Archived items are hidden by default
- Each space can have different status options
