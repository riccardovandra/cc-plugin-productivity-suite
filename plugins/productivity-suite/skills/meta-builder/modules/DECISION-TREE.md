# Decision Tree: Choosing the Right Primitive

Last updated: 2025-12-21

## Quick Decision

| You want to... | Use |
|----------------|-----|
| Add a complex, reusable capability | **Skill** |
| Create a quick action triggered with `/` | **Command** |
| Run work in parallel / isolated context | **Agent** |
| Store project instructions / rules | **Memory** |
| Configure permissions / environment | **Settings** |
| React to tool calls or events | **Hooks** |
| Integrate external tools | **MCP Server** |
| Change how Claude communicates | **Output Style** |
| Package and distribute capabilities | **Plugin** |

---

## Flowchart

```
START: What do you want to add?
│
├─► "A capability (workflow, domain expertise)"
│   │
│   ├─► "Should it trigger automatically based on context?"
│   │   │
│   │   ├─► YES: "Does it need isolated context?"
│   │   │   │
│   │   │   ├─► YES (parallel work) → AGENT
│   │   │   │   Examples: researcher, lead-specialist, doc-updater
│   │   │   │
│   │   │   └─► NO → SKILL
│   │   │       Examples: lead-generation, content-creation, pdf
│   │   │
│   │   └─► NO (explicit trigger): "Simple or complex?"
│   │       │
│   │       ├─► Simple prompt → COMMAND
│   │       │   Examples: /morning, /eod, /commit
│   │       │
│   │       └─► Complex workflow → SKILL (+ optional /command wrapper)
│   │           Create skill, optionally add command to trigger it
│
├─► "Configuration / Instructions"
│   │
│   ├─► "What kind?"
│   │   │
│   │   ├─► Project instructions, coding standards → MEMORY (CLAUDE.md)
│   │   │   Examples: coding conventions, project context, team practices
│   │   │
│   │   ├─► Path-specific rules → MEMORY (rules/)
│   │   │   Examples: "*.test.ts files use vitest", "src/api/** needs validation"
│   │   │
│   │   ├─► Permissions, env vars, tool config → SETTINGS
│   │   │   Examples: allow Bash, set API keys, model override
│   │   │
│   │   └─► Change output style → OUTPUT STYLE
│   │       Examples: verbose mode, learning mode, business mode
│
├─► "Automation / Event handling"
│   │
│   └─► React to tool calls, lifecycle events → HOOKS
│       Examples: lint before commit, notify on completion, block sensitive files
│
├─► "Integration"
│   │
│   └─► "External tool or service?"
│       │
│       └─► YES → MCP SERVER
│           Examples: GitHub, Slack, database, Stripe, Sentry
│
└─► "Distribution / Sharing"
    │
    └─► Package capabilities for others → PLUGIN
        Bundles: commands, agents, skills, hooks, MCP servers
```

---

## Decision Matrix

| Question | Answer | Result |
|----------|--------|--------|
| Auto-trigger + Same context? | Yes | **Skill** |
| Auto-trigger + Parallel/isolated? | Yes | **Agent** |
| Explicit trigger + Simple? | Yes | **Command** |
| Explicit trigger + Complex? | Yes | **Skill** (+ command) |
| Project instructions / rules? | Yes | **Memory** |
| Permissions / env config? | Yes | **Settings** |
| React to events / tool calls? | Yes | **Hooks** |
| External tools / services? | Yes | **MCP Server** |
| Change output / communication? | Yes | **Output Style** |
| Share as versioned package? | Yes | **Plugin** |

---

## Primitives by Category

### Core Primitives (Add Capabilities)

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Skill** | Complex workflows, domain expertise | Multi-file (`SKILL.md` + modules) |
| **Command** | Quick actions, daily routines | Single file (`.md`) |
| **Agent** | Parallel work, specialists | Single file (`.md`) |

### Configuration Primitives

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Memory** | Instructions, rules, context | `CLAUDE.md`, `.claude/rules/*.md` |
| **Settings** | Permissions, env vars, hooks | `.claude/settings.json` |
| **Output Style** | Communication style | `.claude/output-styles/*.md` |

### Integration Primitives

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Hooks** | Event automation | `settings.json` (hooks key) |
| **MCP Server** | External tools | `.mcp.json` |
| **Plugin** | Distribution | `.claude-plugin/plugin.json` |

---

## Examples by Primitive

### Skills
- `lead-generation` - Multi-step pipeline with scripts
- `content-creation` - YouTube scripts, newsletters
- `pdf` - PDF manipulation toolkit
- `gmail` - Email management and drafting
- `youtube` - Extract transcripts and insights

### Commands
- `/morning` - Generate daily brief
- `/eod` - End of day review
- `/commit` - Git commit with description
- `/checkpoint` - Save conversation state

### Agents
- `researcher` - Deep dive into topics
- `doc-updater` - Fetch and update documentation
- `lead-specialist` - Dedicated lead qualification

### Memory
- `CLAUDE.md` - Project instructions, coding standards
- `.claude/rules/testing.md` - Test file conventions
- `.claude/rules/api.md` - API endpoint patterns (path-specific)
- `.claude/rules/frontend/react.md` - React component rules

### Settings
- Allow Bash commands without prompting
- Set default model
- Configure environment variables
- Define hooks for automation
- Enable/disable plugins
- Auto-approve MCP servers

### Hooks
- Run linter after file edits (PostToolUse)
- Block writes to .env files (PreToolUse)
- Notify on task completion (Stop)
- Add session context (SessionStart)
- Log all bash commands (PreToolUse)

### MCP Servers
- GitHub integration (PRs, issues)
- Slack notifications
- Database access (PostgreSQL)
- Sentry error monitoring
- Stripe payment APIs

### Output Styles
- Verbose/explanatory mode
- Learning mode (asks for input)
- Business analyst mode (non-technical)
- Code reviewer style

### Plugins
- Package of related capabilities
- Shared team tooling
- Community contributions
- Versioned distributions

---

## Hybrid Patterns

### Skill + Command
For complex workflows that user wants to trigger explicitly:
```
.claude/skills/lead-generation/  → The capability
.claude/commands/lead-gen.md     → Explicit trigger (optional)
```

**When to use:**
- Skill should be auto-discoverable
- But user also wants explicit trigger option
- Command simply invokes the skill

### Agent + Skill
For specialists that use specific capabilities:
```
.claude/skills/lead-generation/  → The capability
.claude/agents/lead-specialist.md → Specialist using that capability
```

**When to use:**
- Skill provides the capability
- Agent provides isolated context for parallel work
- Agent can reference skill in its instructions

### Memory + Settings
For project configuration:
```
CLAUDE.md                        → Instructions and context
.claude/rules/                   → Path-specific rules
.claude/settings.json            → Permissions and env vars
```

**When to use:**
- Memory for what to do
- Settings for what's allowed
- Rules for path-specific instructions

### Settings + Hooks
For automation with permissions:
```
.claude/settings.json            → Permissions, env, hooks config
.claude/hooks/format.sh          → Hook script
```

**When to use:**
- Settings define when hooks run
- Hooks define what happens
- Permissions control what's allowed

### Plugin (All-in-one)
For distributing a complete solution:
```
.claude-plugin/
├── plugin.json                  → Manifest
├── commands/                    → Slash commands
├── agents/                      → Subagents
├── skills/                      → Skills
├── hooks/hooks.json             → Event handlers
└── .mcp.json                    → MCP servers
```

**When to use:**
- Sharing with team or community
- Versioned releases
- Bundled functionality
- Reusable across projects

---

## Detailed Decision Questions

### 1. Is this a capability or configuration?

**Capability** (adds new functionality):
- → Skill, Command, or Agent

**Configuration** (modifies behavior):
- → Memory, Settings, Output Style

**Integration** (external tools):
- → Hooks, MCP Server

**Distribution** (package for sharing):
- → Plugin

### 2. For capabilities: How is it triggered?

**Auto-trigger** (Claude decides when):
- Same context → **Skill**
- Isolated context → **Agent**

**User-trigger** (explicit `/command`):
- Simple prompt → **Command**
- Complex workflow → **Skill** (+ optional command)

### 3. For configuration: What does it configure?

**Instructions / Rules**:
- Project-wide → **Memory** (CLAUDE.md)
- Path-specific → **Memory** (rules/)

**Behavior / Permissions**:
- Permissions, env vars → **Settings**
- Communication style → **Output Style**

**Automation**:
- Event-driven actions → **Hooks**

### 4. For integration: What type?

**External service**:
- → **MCP Server**

**Event automation**:
- → **Hooks**

**Distribution**:
- → **Plugin**

---

## Common Scenarios

| Scenario | Solution |
|----------|----------|
| "Run linter after every file edit" | **Hook** (PostToolUse) |
| "Generate lead lists from TAM" | **Skill** (complex workflow) |
| "Quick morning standup" | **Command** (`/morning`) |
| "Research topic in parallel" | **Agent** (isolated context) |
| "Never modify .env files" | **Settings** (deny permissions) or **Hook** (PreToolUse) |
| "Team coding standards" | **Memory** (CLAUDE.md or rules/) |
| "Connect to GitHub" | **MCP Server** |
| "Enable verbose explanations" | **Output Style** |
| "Share workflow with team" | **Plugin** |
| "Different rules for test files" | **Memory** (path-specific rules) |
| "Send notification when done" | **Hook** (Stop event) |
| "Override model for project" | **Settings** (model field) |

---

## Anti-Patterns (What NOT to Do)

❌ **Don't use Command for complex workflows**
- Commands are single-file prompts
- Use Skill for multi-step processes

❌ **Don't use Skill when Command is enough**
- If it's just a quick prompt, use Command
- Skills are for complex, reusable capabilities

❌ **Don't put configuration in Skills**
- Use Memory for instructions
- Use Settings for permissions/env

❌ **Don't duplicate Memory and Settings**
- Memory = what to do
- Settings = what's allowed

❌ **Don't create Agent for simple tasks**
- Agents have context isolation overhead
- Use Skill for same-context work

❌ **Don't hardcode secrets in Settings**
- Use environment variables
- Reference via `${VAR}` syntax

❌ **Don't use Hooks for capabilities**
- Hooks are event-driven automation
- Use Skill/Command for user-facing features

---

## Migration Paths

### Outgrew a Command → Skill
Command got too complex:
```
Before: .claude/commands/complex-task.md
After:  .claude/skills/complex-task/SKILL.md
        .claude/commands/complex-task.md (optional trigger)
```

### Need to Share → Plugin
Project-level primitives → Distributable:
```
Before: .claude/skills/my-skill/
        .claude/commands/my-cmd.md
After:  my-plugin/
        ├── .claude-plugin/plugin.json
        ├── skills/my-skill/
        └── commands/my-cmd.md
```

### Settings Grew → Split
Large settings file → Organized:
```
Before: .claude/settings.json (everything)
After:  .claude/settings.json (permissions, env)
        CLAUDE.md (instructions)
        .claude/rules/ (path-specific)
```

---

Last updated: 2025-12-21
