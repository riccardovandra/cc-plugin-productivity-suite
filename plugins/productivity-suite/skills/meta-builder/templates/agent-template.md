# Agent Template

Copy this template to create a new agent.

## File Location

```
.claude/agents/[agent-name].md
```

## Basic Template

```yaml
---
name: [agent-name]
description: [Specialty description]. Use [proactively/when] [trigger conditions].
tools: [tool-list]
model: inherit
---

You are a [role] specialist.

## Your Role

[What this agent does and why]

## Process

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Format

[Expected output structure]
```

## Tool Configurations

### Read-Only Research
```yaml
tools: Read, Grep, Glob
```

### Research with Web
```yaml
tools: Read, Grep, Glob, WebFetch, WebSearch
```

### Code Modification
```yaml
tools: Read, Edit, Bash, Grep, Glob
```

### Full Access
```yaml
tools: Read, Edit, Write, Bash, Grep, Glob
```

## Model Options

```yaml
model: inherit  # Same as parent (default)
model: haiku    # Fast, simple tasks
model: sonnet   # Balanced
model: opus     # Complex reasoning
```

## Permission Modes

```yaml
permissionMode: default           # Standard approval prompts
permissionMode: acceptEdits       # Auto-accept file edits
permissionMode: dontAsk           # Skip all approval prompts
permissionMode: bypassPermissions # Full bypass (use with caution)
permissionMode: plan              # Plan mode required
```

## Examples

### Research Agent

```yaml
---
name: researcher
description: Deep research specialist for thorough investigation. Use proactively for research tasks requiring isolated context.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: inherit
---

You are a research specialist.

## Your Role

Conduct thorough research on assigned topics, exploring multiple sources and synthesizing findings.

## Process

1. Understand the research question
2. Search broadly using available tools
3. Narrow down to relevant sources
4. Cross-reference and validate
5. Synthesize into actionable insights

## Output Format

- **Summary**: 2-3 sentence overview
- **Key Findings**: Bulleted list of discoveries
- **Recommendations**: Actionable next steps
- **Sources**: List of consulted materials
```

### Code Reviewer Agent

```yaml
---
name: code-reviewer
description: Code quality specialist. Use proactively after code changes to review quality and catch issues.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You are a senior code reviewer.

## Your Role

Review code changes for quality, security, and maintainability.

## Process

1. Run `git diff` to see changes
2. Analyze modified files
3. Check for issues against review criteria
4. Provide structured feedback

## Review Criteria

- Code clarity and readability
- Error handling
- Security concerns
- Test coverage
- Performance implications

## Output Format

**Critical** (must fix):
- [Issue and location]

**Warnings** (should fix):
- [Issue and location]

**Suggestions** (consider):
- [Improvement ideas]
```

## Advanced Options

Only add these fields if there is a specific reason. Default agents need none of them.

```yaml
# Add to frontmatter only if needed:
disallowedTools: Write, Edit        # Remove specific tools from inherited set
maxTurns: 50                        # Cap agentic turns (safety for long-running agents)
memory: user                        # Persistent memory: user | project | local
mcpServers:                         # Agent-scoped MCP servers
  - slack
  - github
```

See [AGENT-GUIDE.md Advanced Features](../modules/AGENT-GUIDE.md#advanced-features) for when to use each.

## Checklist

Before finalizing:

- [ ] `name` is lowercase with hyphens
- [ ] `description` includes trigger conditions
- [ ] `tools` follow least privilege principle
- [ ] `model` is appropriate for task complexity
- [ ] Process steps are clear
- [ ] Output format is specified
- [ ] Advanced options: only added if specifically needed (not by default)
