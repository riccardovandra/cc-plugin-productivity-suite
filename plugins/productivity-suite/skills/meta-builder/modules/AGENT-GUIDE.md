# Creating Agents

Agents (subagents) are specialists that run in isolated context for parallel work.

Last updated: 2026-02-19

## When to Create an Agent

- Work should happen in parallel
- Needs isolated context (won't pollute main conversation)
- Specialist that can be delegated to
- Deep research or analysis tasks

## File Locations

| Scope | Location | Priority |
|-------|----------|----------|
| Project | `.claude/agents/` | Higher |
| Personal | `~/.claude/agents/` | Lower |

## Structure

Single markdown file:
```
.claude/agents/agent-name.md
```

## Agent File Format

### YAML Frontmatter

```yaml
---
name: agent-name
description: What this agent specializes in. Use proactively when [trigger conditions].
tools: Read, Edit, Bash, Grep, Glob
model: inherit
permissionMode: default
skills: skill1, skill2
---
```

**Standard Fields:**

| Field | Required | Options | Description |
|-------|----------|---------|-------------|
| `name` | Yes | lowercase with hyphens | Unique identifier |
| `description` | Yes | text | Purpose + when to use (include "proactively" for auto-delegation) |
| `tools` | No | comma-separated | Available tools (inherits all if omitted) |
| `model` | No | `inherit`, `sonnet`, `opus`, `haiku` | Model to use |
| `permissionMode` | No | `default`, `acceptEdits`, `bypassPermissions`, `dontAsk`, `plan` | How to handle permissions |
| `skills` | No | comma-separated | Skills to auto-load on startup |

**Advanced Fields** (see [Advanced Features](#advanced-features) section):

| Field | Description |
|-------|-------------|
| `disallowedTools` | Denylist — removes specific tools from the inherited set |
| `maxTurns` | Cap agentic turns (e.g. `50`) — safety limit for long-running agents |
| `memory` | `user`, `project`, or `local` — enables persistent cross-session memory |
| `mcpServers` | MCP servers available only to this agent (list of server names) |
| `hooks` | Lifecycle hooks scoped to this agent only |

### Markdown Body

The body contains the agent's system prompt:

```markdown
---
name: researcher
description: Deep research specialist. Use proactively for research tasks requiring isolated context.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: inherit
---

You are a research specialist focused on thorough investigation.

## Your Role

- Conduct deep research on topics
- Explore codebases and documentation
- Synthesize findings into actionable insights

## Process

1. Understand the research question
2. Search broadly, then narrow down
3. Cross-reference multiple sources
4. Summarize key findings

## Output Format

Provide:
- Executive summary (2-3 sentences)
- Key findings (bulleted list)
- Recommendations (if applicable)
- Sources consulted
```

## Tool Access

### Common Tool Sets

**Read-only research:**
```yaml
tools: Read, Grep, Glob
```

**Research with web access:**
```yaml
tools: Read, Grep, Glob, WebFetch, WebSearch
```

**Full access:**
```yaml
tools: Read, Edit, Bash, Grep, Glob
```

### Model Selection

- `inherit` - Same as parent conversation
- `haiku` - Fast, lightweight tasks
- `sonnet` - Balanced (default for most)
- `opus` - Complex reasoning

## Built-in Agents

Claude Code includes these built-in agents:

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| `general-purpose` | Sonnet | All | Complex multi-step tasks |
| `plan` | Sonnet | Read, Glob, Grep, Bash | Codebase research in plan mode |
| `explore` | Haiku | Read-only | Fast codebase searching |

## Management

### Using `/agents` Command

```
/agents
```

Interactive interface to:
- View all agents (built-in, user, project)
- Create new agents
- Edit existing agents
- Delete custom agents
- Manage tool permissions

### CLI Configuration

Define agents dynamically with `--agents` flag:

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

## Resumable Agents

Agents can be resumed to continue previous conversations:

- Each execution gets a unique `agentId`
- Transcript stored in: `agent-{agentId}.jsonl`
- Resume with: `resume: "abc123"` parameter

**Use cases:**
- Long-running research
- Iterative refinement
- Multi-step workflows

## Best Practices

### 1. Single Responsibility

One agent = one specialty:
- `researcher` - Deep research
- `doc-updater` - Documentation updates
- `lead-specialist` - Lead qualification

### 2. Include Trigger Conditions

Use "proactively" in description for auto-delegation:
```yaml
description: Review code quality. Use proactively after code changes.
```

### 3. Limit Tool Access

Principle of least privilege:
```yaml
# Read-only agent
tools: Read, Grep, Glob

# Not this:
tools: Read, Edit, Bash, Grep, Glob, Write
```

### 4. Define Clear Process

Include step-by-step process in the body:
```markdown
## Process

1. First, do X
2. Then, do Y
3. Finally, output Z
```

### 5. Specify Output Format

Be explicit about expected output:
```markdown
## Output Format

Return a JSON object with:
- summary: string
- findings: array
- confidence: number
```

## Advanced Features

Only add these when you have a specific reason. A standard agent needs none of them.

### Persistent Memory

When an agent should accumulate knowledge across sessions (not just within one session):

```yaml
memory: user    # Stored in ~/.claude/agent-memory/<name>/MEMORY.md
```

Options:
- `user` — personal, across all projects
- `project` — stored in project scope
- `local` — personal, this project only (gitignored)

The first 200 lines of `MEMORY.md` are injected at agent startup. Use it for patterns, preferences, and accumulated insights.

Use when: the agent's value grows with repeated use (e.g. a researcher that learns your preferences, a lead specialist that accumulates contact patterns).

### Tool Denylist

Remove specific tools from an agent that inherits everything:

```yaml
tools: Read, Edit, Bash, Grep, Glob    # Allowlist (specify exactly what's allowed)
# OR
disallowedTools: Write, Edit           # Denylist (inherit all, remove these)
```

Use `disallowedTools` when you want most tools but need to block a few specific ones.

### Agent-Scoped MCP

Give an agent access to specific MCP servers not available to the parent:

```yaml
mcpServers:
  - slack
  - github
```

Use when: the agent needs integrations that shouldn't be available in the main conversation.

### Max Turns

Cap how many agentic turns the agent can take:

```yaml
maxTurns: 50
```

Use when: preventing runaway agents in production workflows or automated pipelines.

## Template

Use [agent-template.md](../templates/agent-template.md) to create new agents.
