# Read Conversations

Read message history from channels, DMs, or threads.

## Usage

```bash
# Read recent messages from a channel
uv run scripts/read.py --channel C1234567890

# Read more messages
uv run scripts/read.py --channel C1234567890 --limit 50

# Read a specific thread
uv run scripts/read.py --channel C1234567890 --thread 1234567890.123456

# Show message IDs (for thread reference)
uv run scripts/read.py --channel C1234567890 --show-ids

# JSON output
uv run scripts/read.py --channel C1234567890 --json
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel` | Yes | Channel or DM ID |
| `--limit` | No | Max messages (default: 20) |
| `--thread` | No | Thread timestamp for replies |
| `--show-ids` | No | Show message timestamps |
| `--json` | No | Output as JSON |

## Output Fields

| Field | Description |
|-------|-------------|
| `ts` | Message timestamp (unique ID) |
| `date` | Human-readable date |
| `user_name` | Sender display name |
| `text` | Message content |
| `thread_ts` | Parent thread timestamp |
| `reply_count` | Number of thread replies |
| `reactions` | Emoji reactions |

## Examples

### Read channel history

```bash
uv run scripts/read.py --channel C1234567890
```

Output:
```
=== #engineering (20 messages) ===

**Alice** (2026-01-05 09:30)
  Good morning team! Quick standup update...
  [:thumbsup: 3]

**Bob** (2026-01-05 09:32) - 5 replies
  I found the bug we discussed yesterday.
```

### Read thread replies

First, get the thread timestamp:
```bash
uv run scripts/read.py --channel C1234567890 --show-ids
```

Then read the thread:
```bash
uv run scripts/read.py --channel C1234567890 --thread 1234567890.123456
```

## Finding Channel IDs

Use the list command first:
```bash
uv run scripts/list_channels.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "not_in_channel" error | Bot not invited to channel |
| No messages returned | Channel may be empty or bot lacks history scope |
| Missing thread | Thread timestamp format: `1234567890.123456` |
