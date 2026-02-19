# Status Updates

Update task status or mark tasks as complete.

## Script Usage

### Update Status by ID
```bash
uv run scripts/update_status.py abc123 --status "in progress"
uv run scripts/update_status.py abc123 --status "review"
uv run scripts/update_status.py abc123 --status "complete"
```

### Mark Complete (Shorthand)
```bash
uv run scripts/update_status.py abc123 --complete
```

### Search and Update
```bash
uv run scripts/update_status.py --search "homepage" --status "complete"
uv run scripts/update_status.py --search "api" --complete
```

## Conversational Examples

| User Says | Action |
|-----------|--------|
| "Mark the homepage task as done" | Search "homepage", update to complete |
| "Move API integration to in progress" | Search "API integration", update status |
| "Complete task abc123" | `update_status.py abc123 --complete` |
| "Set review status on the login task" | Search "login", update to review |

## Output Format

```
Updating task: Homepage Redesign
  in progress -> complete

Done! Task status updated.
View in ClickUp: https://app.clickup.com/t/abc123
```

## Important Notes

1. **Status names must match your list's settings** - Use the exact status names defined in ClickUp for that list
2. **Common statuses**: Open, In Progress, Review, Complete, Closed
3. **Case sensitivity**: Status names are generally case-insensitive
4. **Search safety**: If multiple tasks match a search query, the script will list them and exit without making changes

## Error Handling

If the status name doesn't exist in the list, ClickUp will return an error. Check your list's status options with:
```bash
uv run scripts/list_spaces.py  # Shows available statuses per space
```
