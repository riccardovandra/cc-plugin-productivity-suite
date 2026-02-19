---
description: Save conversation checkpoint to workspace/docs for session continuity. Enables seamless handoff between agent sessions.
argument-hint: [topic-name]
---

Create a checkpoint that captures the current conversation state for future session continuity.

## Determine Topic

1. If `$ARGUMENTS` is provided, use it as the topic name
2. If no argument, infer the topic from what we've been working on in this conversation
3. Format topic as title case (e.g., "Claude Code Primitives Implementation")

## Check/Create Folder

1. Check if `workspace/docs/[TODAY's DATE] - [TOPIC]/` exists
   - Date format: `YYYY-MM-DD` (e.g., `2025-12-09`)
2. If folder exists: use it
3. If not: create the folder

## Gather Context

Analyze the current conversation and gather:

- **Summary**: 1-2 sentence overview of work done this session
- **What Was Done**: Categorized list of completed work
- **Key Decisions**: Important choices made with rationale
- **Files Modified**: Table of files created/modified with paths and purpose
- **Current Status**: Where things stand now
- **Next Steps**: Priority actions to continue
- **Files to Read First**: Critical files the next agent should read
- **Open Questions**: Unresolved questions needing attention
- **Reference Materials**: URLs, related docs, plan files

## Write Checkpoint

Create/update `workspace/docs/[DATE] - [TOPIC]/Checkpoint.md` using this format:

```markdown
# Checkpoint: [Topic Name]

**Date:** [TODAY's DATE]
**Status:** [Current Phase/Status]

---

## Summary
[1-2 sentence overview of work done]

---

## What Was Done This Session
### [Category]
1. Item 1
2. Item 2

---

## Key Decisions Made
### [Decision 1]
- **Choice:** What was decided
- **Rationale:** Why

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| [path] | Created/Modified | [why] |

---

## Current Status
[Where things stand now]

---

## Next Steps
1. [Priority action 1]
2. [Priority action 2]
3. [Priority action 3]

---

## Context for Next Session
### Files to Read First
- [path/to/critical/file]
- [path/to/another/file]

### Open Questions
- [Question needing resolution]

### Reference Materials
- [URL or file path]

---

## How to Continue
[Brief instructions for picking up where we left off]
```

## Confirm

After creating the checkpoint, confirm:
> "Checkpoint saved to `workspace/docs/[DATE] - [TOPIC]/Checkpoint.md`. The next agent can read this file to continue where we left off."
