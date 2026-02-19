# Extract Transcript

Pull full meeting transcript from Fireflies.ai.

---

## When to Use

User wants to:
- Get a Fireflies meeting transcript
- Review a conversation/call
- Extract notes from a recorded meeting

---

## Prerequisites

- `FIREFLIES_API_KEY` set in `.env`

---

## Process

### Step 1: List Transcripts

```bash
# Recent transcripts
uv run .claude/skills/fireflies/scripts/fireflies.py list

# Filter by participant
uv run .claude/skills/fireflies/scripts/fireflies.py list --participant "Owen"

# Filter by date range
uv run .claude/skills/fireflies/scripts/fireflies.py list --from-date 2024-12-01 --to-date 2024-12-10

# Combined filters
uv run .claude/skills/fireflies/scripts/fireflies.py list --participant "Owen" --limit 5
```

### Step 2: User Selection

Show the table output and transcript IDs. Ask user which one they want using [transcript-select.md](../prompts/transcript-select.md).

### Step 3: Fetch Transcript

```bash
# Display to console
uv run .claude/skills/fireflies/scripts/fireflies.py get <transcript_id>

# Save to file
uv run .claude/skills/fireflies/scripts/fireflies.py get <transcript_id> --output "context/calls/sales-calls/meeting.md"
```

### Step 4: Ask About Saving

After displaying, use [save-confirm.md](../prompts/save-confirm.md) to ask if user wants to save.

---

## Output Format

```markdown
# Meeting Title

**Date:** 2024-12-10
**Duration:** 45m
**Participants:** Person 1, Person 2

---

## Summary

[AI-generated overview]

## Action Items

- Item 1
- Item 2

---

## Full Transcript

**Speaker 1:** text...

**Speaker 2:** text...
```

---

## Troubleshooting

**No transcripts found:**
- Check API key is valid
- Verify date range format (ISO: YYYY-MM-DD)
- Check participant name spelling

**API errors:**
- Verify `FIREFLIES_API_KEY` in `.env`
- Check Fireflies account has API access enabled

**Empty transcript:**
- Meeting may still be processing
- Recording may not have been enabled
