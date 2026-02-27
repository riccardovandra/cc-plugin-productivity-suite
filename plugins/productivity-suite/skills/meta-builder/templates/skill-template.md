# Skill Template

Copy this template to create a new skill.

## Directory Structure

```
.claude/skills/[skill-name]/
├── SKILL.md              # Required: Entry point
├── modules/              # Optional: Detailed instructions
│   └── [MODULE-NAME].md
├── prompts/              # Optional: Reusable user-facing prompts
│   ├── setup.md          # Initial setup questions
│   └── [workflow]/       # Subfolder for workflow-specific prompts
│       └── step-1.md
└── scripts/              # Optional: Executable scripts
    └── [script-name].py
```

## SKILL.md Template

```yaml
---
name: [skill-name]
description: [What it does]. [When to use it - include trigger terms]. Use when [specific scenarios].
---

# [Skill Title]

[1-2 sentence overview]

## Quick Start

[Most common usage pattern - keep brief]

## Available Operations

| Operation | Description | Module |
|-----------|-------------|--------|
| [Op 1] | [Brief description] | [MODULE-1.md](modules/MODULE-1.md) |
| [Op 2] | [Brief description] | [MODULE-2.md](modules/MODULE-2.md) |

## Scripts

Execute via bash:

```bash
uv run scripts/[script-name].py [args]
```

See each module for detailed usage.
```

## Module Template

```markdown
# [Module Title]

[Overview of this specific operation]

## Prerequisites

- [Required setup]
- [Environment variables]

## Process

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Script Usage

```bash
uv run scripts/[script].py [input] [output]
```

**Arguments:**
- `input`: [Description]
- `output`: [Description]

## Output

[Describe expected output format]

## Troubleshooting

- **[Issue]**: [Solution]
```

## Prompt Template

```markdown
# [Prompt Title]

Ask the user:

> "[Question 1]
> - **[Field 1]**: [Hint or example]
> - **[Field 2]**: [Hint or example]
> - **[Field 3]**: [Hint or example]"
```

**Tips:**
- Keep prompts focused on one topic
- Use bullet points for multiple inputs
- Include examples where helpful
- Reference prompts with: `Load and follow prompts/[name].md`

## Advanced Options

Only add these fields if there is a specific reason. Default skills need none of them.

```yaml
# Add to frontmatter only if needed:
argument-hint: "[arg]"              # Shown in autocomplete
disable-model-invocation: true      # Only user can invoke (use for side-effect skills)
user-invocable: false               # Only Claude can invoke (hidden from / menu)
model: haiku                        # Override model: haiku | sonnet | opus
context: fork                       # Run in isolated subagent context
agent: researcher                   # Agent type to use when context: fork
```

See [SKILL-GUIDE.md Advanced Features](../modules/SKILL-GUIDE.md#advanced-features) for when to use each.

## Checklist

Before finalizing:

- [ ] `name` is lowercase with hyphens only (max 64 chars)
- [ ] `description` is third person with trigger terms (max 1024 chars)
- [ ] SKILL.md body is under 500 lines
- [ ] All module references are one level deep
- [ ] Scripts are in `scripts/` folder
- [ ] User-facing prompts extracted to `prompts/` folder
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] If scripts call AI models: cost-appropriate model selected (see `context/models/`)
- [ ] Advanced options: only added if specifically needed (not by default)
