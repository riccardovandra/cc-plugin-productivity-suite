# Gmail Sort Module

Archive, snooze, and label emails for inbox management.

## Quick Usage

```bash
# Archive (remove from inbox)
uv run scripts/sort.py archive <message_id>

# Archive entire thread
uv run scripts/sort.py archive-thread <thread_id>

# Snooze until later
uv run scripts/sort.py snooze <message_id> --until "tomorrow 9am"

# Add label
uv run scripts/sort.py label <message_id> --label "Follow-up"

# Remove label
uv run scripts/sort.py unlabel <message_id> --label "INBOX"
```

## Archive

Removes the message from inbox. The email is NOT deleted - it moves to "All Mail" and can be found via search.

```bash
# Archive single message
uv run scripts/sort.py archive 18abc123def

# Archive entire conversation
uv run scripts/sort.py archive-thread 18xyz789ghi
```

**This is the primary sorting action** (90% of inbox management).

## Snooze

Temporarily hide a message and resurface it later.

```bash
# Snooze until tomorrow morning
uv run scripts/sort.py snooze 18abc123def --until "tomorrow 9am"

# Snooze until next week
uv run scripts/sort.py snooze 18abc123def --until "monday"

# Snooze for 2 hours
uv run scripts/sort.py snooze 18abc123def --until "2 hours"
```

### Supported Time Formats

| Format | Example |
|--------|---------|
| Tomorrow | `tomorrow`, `tomorrow 9am`, `tomorrow morning` |
| Day of week | `monday`, `tuesday morning` |
| Relative | `2 hours`, `3 days` |
| Next week | `next week` |
| Specific | `2024-12-20 14:00` |

**Note**: Gmail API doesn't have native snooze. This archives the message and provides a reminder time. For true snooze behavior, use Gmail web interface.

## Labels

Organize emails with labels.

### Add Label
```bash
uv run scripts/sort.py label 18abc123def --label "Follow-up"
```

If the label doesn't exist, it will be created.

### Remove Label
```bash
uv run scripts/sort.py unlabel 18abc123def --label "To-review"
```

### Common Labels
- `Follow-up` - Needs response
- `Waiting` - Waiting for someone else
- `Reference` - Save for reference
- `Urgent` - High priority

## Workflow Example

### Inbox Zero Process

1. **Search unread**
   ```bash
   uv run scripts/search.py --unread
   ```

2. **Read message**
   ```bash
   uv run scripts/read.py --thread-id 18xyz789ghi
   ```

3. **Decide and act**:
   - No action needed: `sort.py archive <id>`
   - Need to respond later: `sort.py snooze <id> --until "tomorrow 9am"`
   - Need to track: `sort.py label <id> --label "Follow-up"`
   - Ready to respond: Use `draft.py` then archive

4. **Archive after handling**
   ```bash
   uv run scripts/sort.py archive 18abc123def
   ```

## Batch Processing

For multiple messages, process in sequence:

```bash
# Archive multiple
for id in 18abc123 18def456 18ghi789; do
  uv run scripts/sort.py archive $id
done

# Label multiple
for id in 18abc123 18def456; do
  uv run scripts/sort.py label $id --label "Project-X"
done
```

## Tips

- **Archive liberally** - You can always find it via search
- **Use labels sparingly** - Too many labels become unmanageable
- **Snooze wisely** - For things you'll actually action later
- **Process in batches** - Handle similar emails together
