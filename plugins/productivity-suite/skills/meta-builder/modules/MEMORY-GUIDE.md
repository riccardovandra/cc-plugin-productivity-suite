# Creating Memory

Memory provides instructions and context that persist across sessions through CLAUDE.md and rules files.

## When to Use

- Define project-wide coding standards
- Store team instructions and context
- Path-specific rules for different file types
- Personal preferences across projects
- Organization-wide policies

## Memory Hierarchy

| Tier | Location | Scope | Shared |
|------|----------|-------|--------|
| **Enterprise** | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | All users in organization | Yes (via IT) |
| **Project** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via git | Yes |
| **Project Rules** | `./.claude/rules/*.md` | Team via git | Yes |
| **User** | `~/.claude/CLAUDE.md` | Personal (all projects) | No |
| **Local** | `./CLAUDE.local.md` | Personal (this project only) | No (gitignored) |

**Precedence:** Lower-level memories override higher-level ones. Local > User > Project Rules > Project > Enterprise.

## File Locations

### CLAUDE.md Locations

Both paths are valid and equivalent - use whichever fits your project structure:

```
# Project memory (shared with team)
./CLAUDE.md                      # Option 1: Project root
./.claude/CLAUDE.md              # Option 2: Inside .claude/

# User memory (personal, all projects)
~/.claude/CLAUDE.md

# Local override (personal, this project only)
./CLAUDE.local.md                # Auto-added to .gitignore
```

### Rules Directory

```
.claude/rules/
├── code-style.md               # Coding conventions
├── testing.md                  # Test requirements
├── api.md                      # API patterns
└── frontend/                   # Subdirectory organization
    ├── react.md
    └── styles.md
```

All `.md` files in `.claude/rules/` are automatically loaded. Symlinks are supported for sharing rules across projects.

### User-Level Rules

Personal rules at `~/.claude/rules/` are loaded before project rules. Project rules have higher priority and override user-level rules on conflict.

## Format

### Basic CLAUDE.md

```markdown
# Project Name

You are the orchestration layer for this workspace.

## Coding Standards

- Use 2-space indentation
- TypeScript for all new code
- Test coverage required

## Project Context

- API base: https://api.example.com
- Auth: JWT tokens in localStorage
- DB: PostgreSQL on localhost:5432
```

### Path-Specific Rules

Use YAML frontmatter with `paths` field:

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules

- All endpoints must include input validation
- Use standard error response format
- Include OpenAPI documentation comments
```

**Glob patterns:**
- `**/*.ts` - All TypeScript files
- `src/**/*` - All files under src/
- `{src,lib}/**/*.ts` - Multiple directories
- `*.test.ts, *.spec.ts` - Multiple extensions

## Import Syntax

Include other files using `@path`:

```markdown
See @README for project overview.

Additional context:
- Git workflow: @docs/git-instructions.md
- Deployment: @~/.claude/deploy-process.md

Available npm commands: @package.json
```

**Features:**
- Relative paths: `@docs/file.md`
- Absolute paths: `@/absolute/path/file.md`
- Home directory: `@~/.claude/file.md`
- Max depth: 5 hops (prevents circular imports)
- Not evaluated in code blocks: `` `@example` ``

## Organization Patterns

### Simple Project

```
./CLAUDE.md                     # All instructions in one file
```

### Organized Project

```
.claude/
├── CLAUDE.md                   # Overview + imports
└── rules/
    ├── code-style.md
    ├── testing.md
    ├── api.md
    └── security.md
```

### Large Project

```
.claude/
├── CLAUDE.md                   # Overview + imports
└── rules/
    ├── general.md
    ├── frontend/
    │   ├── react.md
    │   ├── styles.md
    │   └── testing.md
    └── backend/
        ├── api.md
        ├── database.md
        └── security.md
```

## Auto Memory

Claude Code maintains automatic memory at `~/.claude/projects/<project>/memory/MEMORY.md`. The first 200 lines are loaded into context at session start.

Key details:
- Storage is git-based, so all worktrees share the same auto memory
- Subagents can maintain their own auto memory independently
- Use `/memory` to view or edit

## Settings for Memory

### claudeMdExcludes

For monorepos, use `claudeMdExcludes` in settings to skip irrelevant CLAUDE.md files from other teams. Accepts glob patterns matched against absolute file paths.

### Additional Directories

Set `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` environment variable to load CLAUDE.md files from `--add-dir` directories.

## Hooks

### InstructionsLoaded

The `InstructionsLoaded` hook fires when a CLAUDE.md or rules file is loaded. Useful for debugging which memory files are active in a session.

## Best Practices

1. **Be specific** - "Use 2-space indentation" > "Format code properly"
2. **Use structure** - Organize with headings and bullet points
3. **Review periodically** - Update as project evolves
4. **Keep rules focused** - One topic per file in rules/
5. **Use path-specific rules sparingly** - Only when truly necessary
6. **Organize with subdirectories** - Group related rules
7. **Use imports for team docs** - Alternative to duplication

## First Principles for Writing CLAUDE.md

Based on empirical research (arxiv:2602.11988 "Evaluating AGENTS.md") and field experience.

**Key finding:** Context files in their common form decrease task success rates and increase inference cost by 20-23%. The primary failure mode is over-instruction.

| Principle | Rule |
|-----------|------|
| Minimal requirements | Every instruction costs against a ~150-200 budget (~50 consumed by Claude Code's system prompt). Each rule must justify its slot. |
| Universal applicability | If a rule doesn't apply to every task in the project, it belongs in a sub-document or path-scoped rule - not root CLAUDE.md. |
| Never auto-generate | `/init` output is a reference, not a starting point. Manual crafting required - LLM-generated files reduce success rates and increase cost 20-23%. |
| Progressive disclosure | Root CLAUDE.md under ~300 lines. Domain-specific guidance in `.claude/rules/` or referenced sub-documents. |
| Pointers over copies | Reference `file:line` instead of inline code snippets. Snippets go stale; file references point to current truth. |
| Positional priority | Most critical instructions at top and bottom. Instructions buried in the middle get systematically less attention (LLM positional bias). |
| No code style rules | Delegate to linters/formatters via hooks. Style instructions bloat context and degrade instruction-following performance. |
| No repository overviews | Agents explore anyway. Overviews add tokens without reducing file discovery steps. |
| Complexity gates | Universal rules (package manager, file deletion) at root. Domain-specific rules path-scoped or conditional. |
| No reactive hotfixes | One-off behavioral fixes appended to CLAUDE.md dilute instruction-following for all future sessions. Use targeted sub-documents or hooks instead. |

**Empirical evidence:**
- Developer-written minimal files: +4% task success
- LLM-generated files: -0.5 to -2% success, +20-23% inference cost
- Agents follow instructions reliably - excess instructions cause excess work (extra exploration, testing, traversal)
- 95-100% of auto-generated files included repository overviews that provided no measurable benefit

## Memory Commands

```bash
/init      # Bootstrap a CLAUDE.md for your codebase
/memory    # Open memory file in editor
```

View loaded memory files with `/memory` command in Claude Code.

## Lookup Behavior

Claude Code reads memories **recursively** from current working directory up to (but not including) root `/`.

Example: If in `foo/bar/`, it loads:
- `foo/CLAUDE.md`
- `foo/bar/CLAUDE.md`
- `foo/bar/CLAUDE.local.md`
- All files in `foo/bar/.claude/rules/`

## Enterprise Deployment

Deploy organization-wide CLAUDE.md via:
- MDM (Mobile Device Management)
- Group Policy
- Ansible
- Configuration management systems

Place at enterprise policy locations (see hierarchy table above).

## Example: Path-Specific Testing Rules

```markdown
---
paths: **/*.test.ts, **/*.spec.ts
---

# Testing Conventions

- Use Vitest for all tests
- Follow Arrange-Act-Assert pattern
- Mock external dependencies
- Minimum 80% coverage for new code
```

## Example: API-Specific Rules

```markdown
---
paths: src/api/**/*.ts
---

# API Endpoint Standards

- All endpoints return consistent JSON structure
- Use Zod for input validation
- Include rate limiting
- Log all errors with request ID
```

---

Last updated: 2026-03-10
