# Reading Comments

View comments on ClickUp tasks.

## Script Usage

### By Task ID
```bash
uv run scripts/comments.py abc123
uv run scripts/comments.py abc123 --limit 10
uv run scripts/comments.py abc123 --json
```

### Search for Task First
```bash
uv run scripts/comments.py --search "homepage"
```

## Conversational Examples

| User Says | Action |
|-----------|--------|
| "Show comments on the homepage task" | Search "homepage", get comments |
| "What did people say about task abc123?" | `comments.py abc123` |
| "Read the last 5 comments on API integration" | Search, then `--limit 5` |

## Output Format

```
Comments on **Homepage Redesign** (3):

**john** (2025-01-10 14:30):
Looking good! Can we add more spacing to the hero section?
----------------------------------------
**sarah** (2025-01-10 15:45):
Done! Also updated the call-to-action button color.
----------------------------------------
**john** (2025-01-11 09:00):
Perfect, approved for deployment.
----------------------------------------
```

## JSON Output

```bash
uv run scripts/comments.py abc123 --json
```

```json
[
  {
    "id": "comment_123",
    "text": "Looking good! Can we add more spacing to the hero section?",
    "user": "john",
    "date": "2025-01-10 14:30"
  }
]
```

## Notes

- Comments are returned in chronological order (oldest first)
- Use `--limit` to restrict the number of comments returned
- If searching returns multiple tasks, the script will list them and require you to use a task ID
