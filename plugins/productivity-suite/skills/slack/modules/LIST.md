# List Channels

List channels, DMs, and group conversations.

## Usage

```bash
# List all channels (public + private)
uv run scripts/list_channels.py

# List only public channels
uv run scripts/list_channels.py --type public_channel

# List only private channels
uv run scripts/list_channels.py --type private_channel

# List only DMs
uv run scripts/list_channels.py --type im

# Include DMs with channels
uv run scripts/list_channels.py --include-dms

# JSON output
uv run scripts/list_channels.py --json
```

## Channel Types

| Type | Description |
|------|-------------|
| `public_channel` | Public channels anyone can join |
| `private_channel` | Private channels (invite only) |
| `mpim` | Multi-person direct messages |
| `im` | Direct messages (1:1) |

## Output Fields

| Field | Description |
|-------|-------------|
| `id` | Channel ID (use this for other commands) |
| `name` | Channel name |
| `is_private` | Whether channel is private |
| `num_members` | Number of members |
| `topic` | Channel topic |
| `purpose` | Channel purpose/description |

## Examples

### List channels to find IDs

```bash
uv run scripts/list_channels.py
```

Output:
```
=== Channels (15) ===

# general (120 members) - Company announcements
   ID: C1234567890

🔒 engineering (25 members) - Engineering team
   ID: C0987654321
```

### Get JSON for processing

```bash
uv run scripts/list_channels.py --json | jq '.channels[] | {name, id}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No channels shown | Bot not in any channels - invite it |
| Missing private channels | Bot needs `groups:read` scope |
| Missing DMs | Bot needs `im:read` scope |
