# Gmail Read Module

Read individual messages or full conversation threads.

## Quick Usage

```bash
# Read single message
uv run scripts/read.py --message-id 18abc123def

# Read full conversation thread
uv run scripts/read.py --thread-id 18xyz789ghi

# Save to file
uv run scripts/read.py --thread-id 18xyz789ghi --output conversation.json

# Show only headers (no body)
uv run scripts/read.py --thread-id 18xyz789ghi --no-body
```

## Reading Threads vs Messages

### Thread (Conversation)
A thread contains all messages in a conversation chain. Use this to see the full context of a discussion.

```bash
uv run scripts/read.py --thread-id 18xyz789ghi
```

Output:
```
Conversation (3 messages)

======================================================================
From:    Client <client@example.com>
To:      you@example.com
Date:    2024-12-15 10:30
Subject: Project Update
----------------------------------------------------------------------
Hi, here's the latest update on the project...

======================================================================
From:    You <you@example.com>
To:      client@example.com
Date:    2024-12-15 11:45
Subject: Re: Project Update
----------------------------------------------------------------------
Thanks for the update! I have a few questions...

======================================================================
From:    Client <client@example.com>
To:      you@example.com
Date:    2024-12-16 09:00
Subject: Re: Project Update
----------------------------------------------------------------------
Good questions. Let me address them...
```

### Single Message
Read one specific message by ID.

```bash
uv run scripts/read.py --message-id 18abc123def
```

## Output Formats

### Terminal (default)
Formatted for reading in terminal.

### JSON
Full structured data for processing.

```bash
uv run scripts/read.py --thread-id 18xyz789ghi --json
```

```json
{
  "type": "thread",
  "fetched_at": "2024-12-17T10:30:00",
  "thread": {
    "id": "18xyz789ghi",
    "message_count": 3,
    "messages": [
      {
        "id": "18abc123def",
        "thread_id": "18xyz789ghi",
        "labels": ["INBOX", "IMPORTANT"],
        "from": "client@example.com",
        "to": "you@example.com",
        "subject": "Project Update",
        "date": "2024-12-15 10:30",
        "body": "Full message body here..."
      }
    ]
  }
}
```

## Getting IDs

Message and thread IDs come from search results:

```bash
# Search returns IDs
uv run scripts/search.py --query "from:client"

# Output includes:
# ID: 18abc123def  Thread: 18xyz789ghi
```

## Tips

### Save important conversations
```bash
uv run scripts/read.py --thread-id 18xyz789ghi --output workspace/docs/client-conversation.json
```

### Quick scan without bodies
```bash
uv run scripts/read.py --thread-id 18xyz789ghi --no-body
```

### Export for reference
```bash
uv run scripts/read.py --thread-id 18xyz789ghi --json > conversation.json
```

## Next Steps

After reading:
1. **Archive**: `uv run scripts/sort.py archive <message_id>`
2. **Draft reply**: `uv run scripts/draft.py reply --thread-id <thread_id> --body reply.txt`
3. **Label**: `uv run scripts/sort.py label <message_id> --label "Reviewed"`
