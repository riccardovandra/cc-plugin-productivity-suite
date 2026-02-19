---
description: 'Stage all changes and commit with an auto-generated description'
---

# Git Commit

Perform a git commit with an intelligent commit message.

## Instructions

1. Run `git status` to see all changes
2. Run `git diff --staged` and `git diff` to understand what changed
3. Analyze the changes and generate a concise, descriptive commit message that:
   - Starts with a verb (Add, Update, Fix, Remove, Refactor, etc.)
   - Summarizes the main change in under 50 characters for the subject line
   - If needed, add a body with more details

4. Stage all changes: `git add .`
5. Commit with the generated message
6. Push to remote: `git push`
7. Show the result to the user

## Commit Message Format

```
<type>: <short description>

<optional body with more context>
```

Types: Add, Update, Fix, Remove, Refactor, Move, Rename, Document

## Example

If adding new files to workspace:
```
Add project documentation and scripts
```

If fixing something:
```
Fix git commit script error handling
```
