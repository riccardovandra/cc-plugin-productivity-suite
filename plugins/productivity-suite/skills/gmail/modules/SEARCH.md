# Gmail Search Module

Search and list emails using Gmail's powerful search syntax.

## Quick Usage

```bash
# List recent inbox messages
uv run scripts/search.py

# Search with query
uv run scripts/search.py --query "from:client@example.com"

# Unread only
uv run scripts/search.py --unread

# Get more results
uv run scripts/search.py --limit 50

# Save to JSON
uv run scripts/search.py --query "from:client" --output results.json
```

## Gmail Search Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `from:` | Messages from sender | `from:client@example.com` |
| `to:` | Messages to recipient | `to:team@company.com` |
| `subject:` | Word in subject | `subject:invoice` |
| `is:unread` | Unread messages | `is:unread` |
| `is:starred` | Starred messages | `is:starred` |
| `is:important` | Important messages | `is:important` |
| `has:attachment` | Has attachments | `has:attachment` |
| `after:` | After date | `after:2024/01/01` |
| `before:` | Before date | `before:2024/12/31` |
| `older_than:` | Older than period | `older_than:7d` |
| `newer_than:` | Newer than period | `newer_than:2d` |
| `label:` | Has label | `label:work` |
| `in:inbox` | In inbox | `in:inbox` |
| `in:sent` | In sent mail | `in:sent` |
| `in:trash` | In trash | `in:trash` |
| `-` | Exclude | `-newsletter` |
| `OR` | Either condition | `from:a OR from:b` |
| `()` | Grouping | `(from:a OR from:b) is:unread` |

## Common Search Patterns

### Find emails from someone
```bash
uv run scripts/search.py --query "from:client@example.com"
```

### Find recent conversation
```bash
uv run scripts/search.py --query "from:john OR to:john newer_than:7d"
```

### Find unread with attachments
```bash
uv run scripts/search.py --query "is:unread has:attachment"
```

### Find by subject keyword
```bash
uv run scripts/search.py --query "subject:invoice after:2024/01/01"
```

### Find emails to follow up
```bash
uv run scripts/search.py --query "from:me is:sent older_than:3d -has:reply"
```

## Output Format

### Table output (default)
```
DATE        SENDER                     SUBJECT
--------------------------------------------------------------------------------
2024-12-17  John Smith                 Meeting Tomorrow
            ID: 18abc123def  Thread: 18xyz789ghi
```

### JSON output
```bash
uv run scripts/search.py --query "is:unread" --json
```

Returns:
```json
{
  "query": "is:unread",
  "searched_at": "2024-12-17T10:30:00",
  "count": 5,
  "messages": [
    {
      "id": "18abc123def",
      "thread_id": "18xyz789ghi",
      "from": "John Smith <john@example.com>",
      "to": "me@example.com",
      "subject": "Meeting Tomorrow",
      "date": "2024-12-17 09:15",
      "snippet": "Hi, just wanted to confirm..."
    }
  ]
}
```

## Next Steps

After finding emails:
1. **Read full thread**: `uv run scripts/read.py --thread-id <thread_id>`
2. **Archive**: `uv run scripts/sort.py archive <message_id>`
3. **Draft reply**: `uv run scripts/draft.py reply --thread-id <thread_id>`
