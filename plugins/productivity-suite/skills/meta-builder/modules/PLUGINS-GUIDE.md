# Creating Plugins

Plugins package Claude Code capabilities (commands, agents, skills, hooks, MCP servers) for distribution and sharing.

## When to Use

- Share capabilities across multiple projects
- Distribute to team or community
- Version capabilities with semantic versioning
- Bundle related functionality together
- Require reusable tools across workspaces

## Plugin vs Standalone

| Aspect | Standalone (`.claude/`) | Plugins |
|--------|------------------------|---------|
| Scope | Single project | Shareable across projects |
| Commands | `/hello` | `/plugin-name:hello` |
| Versioning | Manual | Semantic versioning |
| Distribution | Git only | Marketplaces |
| Best For | Personal workflows | Team/community |

**Use plugins when:** Sharing with teams, community distribution, versioned releases, or reusable across projects.

## Structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required: manifest
├── commands/                # Slash commands
│   └── hello.md
├── agents/                  # Custom agents
│   └── specialist.md
├── skills/                  # Agent Skills
│   └── my-skill/
│       └── SKILL.md
├── hooks/                   # Event handlers
│   └── hooks.json
├── .mcp.json               # MCP servers
├── .lsp.json               # LSP servers
└── README.md               # Documentation
```

**Important:** Only `plugin.json` goes in `.claude-plugin/`. All other directories are at plugin root.

### settings.json

A `settings.json` at plugin root provides default plugin settings. Currently only the `agent` key is supported, which activates a plugin agent as the main thread:

```json
{
  "agent": "specialist"
}
```

### .lsp.json

A `.lsp.json` at plugin root enables language intelligence (LSP server support). This gives Claude Code access to language-aware features like go-to-definition, references, and diagnostics for the configured languages.

## Format

### Plugin Manifest (plugin.json)

**Minimal:**
```json
{
  "name": "my-plugin",
  "description": "Brief description",
  "version": "1.0.0"
}
```

**Complete:**
```json
{
  "name": "my-plugin",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "email@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["automation", "ci-cd"],
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

**Required fields:**
- `name` - Unique identifier (kebab-case, no spaces)
- `version` - Semantic versioning (e.g., "1.0.0")
- `description` - Brief description

**Optional metadata:**
- `author` - Attribution
- `homepage` - Documentation URL
- `repository` - Source code URL
- `license` - License type (e.g., "MIT", "Apache-2.0")
- `keywords` - Search tags

**Component paths** (all optional, default to standard locations):
- `commands` - Path to commands directory
- `agents` - Path to agents directory
- `skills` - Path to skills directory
- `hooks` - Path to hooks.json
- `mcpServers` - Path to .mcp.json
- `outputStyles` - Path to output-styles directory
- `lspServers` - Path to .lsp.json

## Plugin Components

### 1. Slash Commands

**Location:** `commands/` directory

**Example: `commands/hello.md`**
```markdown
---
description: Greet the user
---

# Hello Command

Greet the user named "$ARGUMENTS" warmly.
```

**Usage:** `/my-plugin:hello Alex`

### 2. Agents

**Location:** `agents/` directory

**Example: `agents/specialist.md`**
```markdown
---
name: specialist
description: Domain expert. Use proactively for specialized tasks.
tools: Read, Grep, Glob
model: inherit
---

You are a specialist in [domain].

[Agent instructions...]
```

### 3. Skills

**Location:** `skills/` directory

**Example: `skills/my-skill/SKILL.md`**
```markdown
---
name: my-skill
description: What it does and when to use it.
---

# My Skill

[Skill instructions...]
```

### 4. Hooks

**Location:** `hooks/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
          }
        ]
      }
    ]
  }
}
```

**Use `${CLAUDE_PLUGIN_ROOT}`** for plugin-relative paths.

### 5. MCP Servers

**Location:** `.mcp.json`

```json
{
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

### 6. LSP Servers

**Location:** `.lsp.json`

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

## Environment Variables

**`${CLAUDE_PLUGIN_ROOT}`** - Absolute path to plugin directory

Use in:
- Hooks
- MCP servers
- Scripts

**Example:**
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
}
```

## Development & Testing

### Load Plugin Locally

Use `--plugin-dir` for local development testing without installing:

```bash
# Single plugin
claude --plugin-dir ./my-plugin

# Multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two

# Test from anywhere with absolute path
claude --plugin-dir /path/to/my-plugin
```

### Test Components

```bash
# Test commands
/my-plugin:command-name

# Check agents
/agents

# Verify skills work
# Skills auto-activate based on context
```

## Installation & Distribution

### Installation Scopes

| Scope | File | Use Case |
|-------|------|----------|
| **user** | `~/.claude/settings.json` | Personal (default) |
| **project** | `.claude/settings.json` | Team via git |
| **local** | `.claude/settings.local.json` | Project-specific |
| **managed** | `managed-settings.json` | Enterprise |

### Install Commands

```bash
# Install plugin
claude plugin install <plugin> [--scope user|project|local]

# Uninstall
claude plugin uninstall <plugin> [--scope user|project|local]

# Enable/Disable
claude plugin enable <plugin> [--scope user|project|local]
claude plugin disable <plugin> [--scope user|project|local]

# Update
claude plugin update <plugin> [--scope user|project|local|managed]
```

### Version Management

Use semantic versioning: `MAJOR.MINOR.PATCH`

- `1.0.0` → `1.1.0` - New features (backward-compatible)
- `1.0.0` → `2.0.0` - Breaking changes
- `1.0.0` → `1.0.1` - Bug fixes

## Migration from Standalone

### Convert `.claude/` to Plugin

1. **Create plugin structure:**
```bash
mkdir -p my-plugin/.claude-plugin
```

2. **Create manifest:**
```json
{
  "name": "my-plugin",
  "description": "Migrated from standalone",
  "version": "1.0.0"
}
```

3. **Copy components:**
```bash
cp -r .claude/commands my-plugin/
cp -r .claude/agents my-plugin/
cp -r .claude/skills my-plugin/
```

4. **Migrate hooks:**

Extract from `.claude/settings.json` → `my-plugin/hooks/hooks.json`

5. **Test:**
```bash
claude --plugin-dir ./my-plugin
```

## Best Practices

1. **Add comprehensive README**
   - Installation instructions
   - Component descriptions
   - Usage examples
   - Configuration options

2. **Version properly**
   - Semantic versioning
   - Changelog for each version
   - Document breaking changes

3. **Use plugin-relative paths**
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/helper.sh"
}
```

4. **Test before distributing**
   - Load locally first
   - Test all components
   - Verify with team

5. **Organize components**
```
my-plugin/
├── .claude-plugin/plugin.json
├── commands/
├── agents/
├── skills/
├── scripts/           # Helper scripts
├── hooks/
├── README.md
├── LICENSE
└── CHANGELOG.md
```

6. **Document dependencies**

In README:
```markdown
## Requirements

- Python 3.8+
- Node.js 18+
- npx available
```

7. **Handle errors gracefully**

In hooks and scripts:
```bash
#!/bin/bash
set -euo pipefail

# Error handling
if [[ ! -f "$required_file" ]]; then
  echo "Error: Required file not found" >&2
  exit 1
fi
```

## Example: Complete Plugin

**Structure:**
```
formatter-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── format-all.md
├── hooks/
│   └── hooks.json
├── scripts/
│   └── format.sh
└── README.md
```

**.claude-plugin/plugin.json:**
```json
{
  "name": "formatter",
  "version": "1.0.0",
  "description": "Auto-format code on save",
  "author": {
    "name": "Dev Team"
  },
  "license": "MIT"
}
```

**commands/format-all.md:**
```markdown
---
description: Format all project files
---

# Format All

Run prettier on all supported files in the project.
```

**hooks/hooks.json:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
          }
        ]
      }
    ]
  }
}
```

**scripts/format.sh:**
```bash
#!/bin/bash
set -euo pipefail

file_path=$(jq -r '.tool_input.file_path // empty')

if [[ "$file_path" =~ \.(ts|js|tsx|jsx)$ ]]; then
  npx prettier --write "$file_path"
  echo "✓ Formatted $file_path"
fi

exit 0
```

**README.md:**
```markdown
# Formatter Plugin

Auto-format code on save using Prettier.

## Installation

```bash
claude plugin install formatter --scope user
```

## Usage

Files are automatically formatted on save.

Manually format all files:
```
/formatter:format-all
```

## Requirements

- Node.js 18+
- npx available
```

## Plugin Submission

To submit a plugin for public distribution:

- **Claude.ai:** `https://claude.ai/settings/plugins/submit`
- **Platform:** `https://platform.claude.com/plugins/submit`

## Debugging

```bash
# Enable debug mode
claude --debug

# Check loaded plugins
/plugin

# Verify components
/commands  # Check commands
/agents    # Check agents
```

## Path Behavior

- Custom paths **supplement** defaults (don't replace)
- Paths must be relative and start with `./`
- Plugins are copied to cache (not used in-place)
- Path traversal (`../`) won't work

**Solution for shared files:**
- Use symlinks within plugin
- Or set marketplace source to parent directory

---

Last updated: 2026-03-10
