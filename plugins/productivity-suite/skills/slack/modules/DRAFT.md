# Draft Messages

Create draft messages saved locally. **Does NOT send to Slack.**

## Usage

```bash
# Create a draft with inline message
uv run scripts/draft.py --channel C1234567890 --message "Hello team!"

# Create a draft from file
uv run scripts/draft.py --channel C1234567890 --file message.txt

# Create a thread reply draft
uv run scripts/draft.py --channel C1234567890 --message "Reply" --thread 1234567890.123456

# Custom output directory
uv run scripts/draft.py --channel C1234567890 --message "Hi" --output-dir ./drafts

# JSON output
uv run scripts/draft.py --channel C1234567890 --message "Hi" --json
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel` | Yes | Channel or DM ID |
| `--message` | One of | Message text |
| `--file` | One of | Read message from file |
| `--thread` | No | Thread timestamp for reply |
| `--output-dir` | No | Save location |
| `--json` | No | Output as JSON |

## Output Location

By default, drafts are saved to:
```
workspace/docs/YYYY-MM-DD - Slack Drafts/draft-channelname-HHMMSS.md
```

## Draft File Format

```markdown
# Slack Draft Message

**Channel:** #engineering
**Channel ID:** `C1234567890`
**Created:** 2026-01-05 10:30:00

---

## Message

Hello team! Here's my update...

---

## How to Send

1. Open Slack
2. Go to #engineering
3. Paste the message above and send
```

## Examples

### Quick message draft

```bash
uv run scripts/draft.py --channel C1234567890 --message "Quick update: the deploy is complete!"
```

### Long message from file

Create `update.txt`:
```
Team,

Here's the weekly summary:

- Feature A: Complete
- Feature B: In progress
- Bug fixes: 12 resolved

Let me know if you have questions!
```

Then:
```bash
uv run scripts/draft.py --channel C1234567890 --file update.txt
```

### Thread reply draft

```bash
uv run scripts/draft.py \
  --channel C1234567890 \
  --thread 1234567890.123456 \
  --message "Great point! I'll follow up on this."
```

## Why Drafts?

This skill intentionally does NOT send messages because:

1. **Safety** - Review before sending
2. **Control** - User decides when to send
3. **Audit** - Local record of drafted messages
4. **Formatting** - Check message looks correct

To send messages, manually copy from the draft file and paste in Slack.
