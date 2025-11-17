<table>
<tr>
<td width="300" align="center">
  <img src="logo.jpg" alt="Agent Warden Logo" width="300"/>
</td>
<td>

# Agent Warden

**Centralized Rules & Commands Manager for AI Coding Assistants**

Sync Cursor Rules, Augment Rules, Claude Rules & Custom Commands Across All Your Projects

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

</td>
</tr>
</table>

---

**Stop copying `.cursor/rules`, `.augment/rules`, and `.claude/rules` between projects!**

Agent Warden is a powerful command-line tool that manages and synchronizes AI coding assistant rules and custom commands across multiple projects. Whether you're using Cursor, Augment, Claude Code, Windsurf, or Codex, Agent Warden keeps your AI assistant configurations consistent and up-to-date.

## Demo

![Agent Warden Demo](vhs-demo/agent-warden-demo.gif)

*Watch Agent Warden in action: install rules, track changes, update projects, and sync across all your projects.*

**Perfect for:**

- Teams using multiple AI coding assistants (Cursor + Augment + Claude)
- Developers managing rules across many projects
- Keeping AI assistant configurations synchronized
- Sharing custom rules and commands with your team
- Enterprise teams standardizing AI coding practices

**Key Features:**

- Centralized management of `.cursor/rules`, `.augment/rules`, `.claude/rules`
- Sync rules and commands across unlimited projects
- Support for Cursor, Augment, Claude Code, Windsurf, and Codex
- GitHub package system for sharing team rules
- Version control and conflict detection
- Symlinks or copies - your choice

## Why Agent Warden?

**The Problem:** You're using Cursor, Augment, or Claude Code across multiple projects. Each project needs the same coding rules, commit standards, and custom commands. You end up:

- Manually copying `.cursor/rules` files between projects
- Updating rules in 10+ projects when standards change
- Forgetting which projects have which rules
- Dealing with inconsistent AI assistant behavior across projects

**The Solution:** Agent Warden centralizes your AI coding assistant rules and commands. Update once, sync everywhere.

```bash
# Install rules to all your projects at once
warden install ~/project1 --rules coding-standards git-commit
warden install ~/project2 --rules coding-standards git-commit
warden install ~/project3 --rules coding-standards git-commit

# Update the rule once, sync to all projects with one command
warden project update
```

## Quick Start

```bash
# Install Agent Warden
pip install -e .

# Install Cursor rules to a project
warden install ~/my-project --target cursor --rules coding-no-emoji

# Add Augment rules to the same project
warden install ~/my-project --target augment --rules coding-no-emoji

# List all managed projects
warden project list

# Update all projects when rules change
warden status  # Check what needs updating
warden project update my-project --all
```

## Remote SSH Support

Agent Warden supports managing rules and commands on **remote machines via SSH**! This is perfect for:

- Managing rules on remote development servers
- Deploying AI assistant configurations to cloud instances
- Keeping remote projects synchronized with your local standards
- Managing rules on multiple remote machines from one location

### Remote Installation

Use standard SSH location format: `[user@]host:path`

```bash
# Install rules to a remote server
warden install user@server.com:/var/www/project --target augment --rules coding-no-emoji

# Using SSH config alias
warden install myserver:/home/dev/app --target cursor --rules git-commit

# Without explicit user (uses SSH config)
warden install server:/remote/path --target augment --rules coding-standards
```

### How It Works

1. **SSH Configuration**: Agent Warden relies on your `~/.ssh/config` for authentication
   - No need to configure SSH keys separately
   - Supports all SSH features (ProxyJump, IdentityFile, Port, etc.)
   - Uses your existing SSH setup

2. **File Transfer**: Automatically uses `rsync` (preferred) or `scp` for efficient file transfer
   - Checksums verified on remote
   - Atomic operations
   - Compression for large files

3. **State Management**: Project state is stored **locally only**
   - Your local system tracks which remote projects have which rules
   - Remote machines don't need Agent Warden installed
   - Update detection works the same as local projects

4. **Copy Mode**: Remote installations always use copy mode (symlinks not supported)

   ```bash
   # Remote automatically uses copy mode
   warden install server:/path --target augment --rules my-rule
   # [INFO] Remote locations require file copies (symlinks not supported)
   ```

### SSH Configuration Example

Set up your `~/.ssh/config` once:

```ssh-config
Host myserver
    HostName server.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/deploy_key

Host production
    HostName prod.example.com
    User app
    ProxyJump bastion.example.com
```

Then use simple aliases in Agent Warden:

```bash
warden install myserver:/var/www/app --target augment --rules coding-standards
warden install production:/opt/service --target cursor --rules git-commit
```

### Remote Operations

All standard operations work with remote projects:

```bash
# List all projects (local and remote)
warden project list

# Update remote project
warden project update my-remote-project

# Check status of remote project
warden status my-remote-project

# Add more rules to remote project
warden install --project my-remote-project --rules new-rule

# Remove remote project from tracking
warden project remove my-remote-project
```

### Requirements

- **SSH client** installed (`ssh`, `scp`, `rsync`)
- **SSH access** configured to remote machine (via `~/.ssh/config` or SSH keys)
- **Write permissions** on remote project directory
- **Network connectivity** to remote machine
- **Note:** Remote machine does NOT need Agent Warden installed

### File Transfer Details

Agent Warden uses intelligent file transfer:

1. **Preferred method: `rsync`**
   - Efficient delta transfers (only changed parts)
   - Preserves timestamps and permissions
   - Atomic operations with checksums
   - Compression for large files

2. **Fallback method: `scp`**
   - Used if `rsync` is not available on remote
   - Full file transfers
   - Still reliable and secure

3. **Copy mode only**
   - Remote installations always use copy mode
   - Symlinks cannot span SSH connections
   - Files are fully copied to remote machine

### Controlling Remote Updates

By default, global update commands (`warden project update` and `warden status`) include remote projects. You can disable this if you have remote projects that require password authentication or are temporarily unavailable:

```bash
# Disable remote project updates in global commands
warden config --update-remote false

# Check status (will skip remote projects)
warden status

# Update all projects (will skip remote projects)
warden project update

# Re-enable remote project updates
warden config --update-remote true

# View current setting
warden config --show
```

**Note:** Individual remote projects can still be updated directly:

```bash
# This always works, regardless of the global setting
warden project update my-remote-project
```

**Use cases for disabling remote updates:**

- Remote servers require password authentication (would interrupt automated updates)
- Temporary network issues or VPN disconnections
- Remote servers are offline or under maintenance
- You want to update only local projects quickly

### Troubleshooting Remote Connections

```bash
# Test SSH connection first
ssh user@server.com 'echo "Connection successful"'

# Check if rsync is available
which rsync

# Verify remote path exists
ssh user@server.com 'ls -la /var/www/project'

# Check Agent Warden error messages
warden install user@server:/path --target augment --rules test-rule
# Error messages will indicate connection, permission, or path issues
```

## Supported AI Coding Assistants

| Assistant | Rules Support | Commands Support | Config Path | Notes |
|-----------|--------------|------------------|-------------|-------|
| **Cursor** | ✅ `.cursor/rules/` | ❌ | Project-level | Supports symlinks |
| **Augment** | ✅ `.augment/rules/` | ✅ `.augment/commands/` | Project-level | **Copy mode only** |
| **Claude Code** | ✅ `.claude/rules/` | ✅ `.claude/commands/` | Project + Global | Supports symlinks |
| **Windsurf** | ✅ `.windsurf/rules/` | ❌ | Project + Global | Supports symlinks |
| **Codex** | ✅ `.codex/rules/` | ✅ `.codex/commands/` | Project + Global | Supports symlinks |

**Note**: Augment always uses copy mode because its file watching system doesn't follow symlinks. This is handled automatically by Agent Warden.

## Important: Meta-Rules vs Project Rules

**The built-in `mdc.mdc` file is a meta-rule** that defines the MDC (Markdown Documentation Convention) format itself. It serves as documentation and guidance for AI agents on how to create proper MDC files, but it's not meant to be installed in projects.

**For actual project rules**, you have two options:

1. **Built-in Rules** (in `rules/` directory): General-purpose rules like `coding-standards.mdc` that can be used across projects
2. **Package Rules** (from GitHub): Project-specific or framework-specific rules from GitHub packages (e.g., TypeScript rules, Python rules, security rules, etc.)

## Creating Custom Rules with AI Agents

**Use your AI coding assistant to create custom rules!** The `mdc.mdc` meta-rule teaches AI agents how to write proper MDC rule files.

### Method 1: Ask Your AI Assistant Directly

If you have `mdc.mdc` installed in your project (or in your AI assistant's global config), simply ask:

```
"Using mdc.mdc, create a rule called 'api-design.mdc' that enforces:
- RESTful naming conventions
- Proper HTTP status codes
- Consistent error response format
- API versioning in URLs"
```

Your AI assistant will generate a properly formatted MDC rule file that you can save to `rules/api-design.mdc`.

### Method 2: Use Agent Warden's Built-in mdc.mdc

```bash
# Install mdc.mdc to your AI assistant's global config
warden global-install cursor  # or augment, claude, etc.

# Now ask your AI assistant to create rules using the MDC format
# Example prompts:
# - "Create an MDC rule for TypeScript naming conventions"
# - "Write an MDC rule enforcing security best practices"
# - "Generate an MDC rule for React component structure"
```

### Method 3: Create Rules Manually

1. Look at existing rules in `rules/` for examples
2. Follow the MDC format (frontmatter + markdown content)
3. Save to `rules/your-rule-name.mdc`
4. Install to projects: `warden install ~/project --rules your-rule-name`

### Example: Creating a TypeScript Rule

Ask your AI assistant:

```
"Using mdc.mdc, create a rule called 'typescript-strict.mdc' that enforces:
- Strict TypeScript configuration
- No 'any' types
- Explicit return types on functions
- Interface over type aliases for object shapes"
```

The AI will generate something like:

```markdown
---
description: Enforce strict TypeScript practices
globs: ["**/*.ts", "**/*.tsx"]
---

# TypeScript Strict Mode

Always use strict TypeScript configuration...
```

Save this to `rules/typescript-strict.mdc` and install it:

```bash
warden install ~/my-project --rules typescript-strict
```

## Using Example Rules and Commands

Agent Warden includes example rules and commands in `rules/example/` and `commands/example/` directories. These are for reference only and are **not** automatically available for installation.

### Available Examples

**Rules:**

- `coding-no-emoji.mdc` - Enforces no emojis in code
- `git-commit.mdc` - Git commit message standards with atomic commits

**Commands:**

- `code-review.md` - Comprehensive code review
- `test-gen.md` - Generate unit tests
- `refactor.md` - Code refactoring suggestions
- `api-design.md` - API design and documentation

### Using Examples

To use an example rule or command, copy it out of the `example/` directory:

```bash
# Copy an example rule to make it available
cp rules/example/coding-no-emoji.mdc rules/

# Copy an example command
cp commands/example/code-review.md commands/

# Now you can install them to projects
warden install /path/to/project --rules coding-no-emoji --commands code-review
```

## Creating Custom Rules

You can create your own rules in the `rules/` directory following the MDC format defined in `mdc.mdc`.

### Creating Your Own Rule

1. Create a new `.mdc` file in the `rules/` directory (not in `example/`)
2. Follow the MDC format with frontmatter and annotations
3. Package it or share it via GitHub for team use

```bash
# Create a new rule
cat > rules/my-custom-rule.mdc << 'EOF'
---
description: My custom coding rule for the team
globs: ["**/*.ts", "**/*.tsx"]
---

# My Custom Rule

@context {
    "type": "guidelines",
    "purpose": "team_standards"
}

## Rule Details
...
EOF
```

## Features

### AI Coding Assistant Rules Management

- **Multi-Assistant Support**: Manage rules for Cursor, Augment, Claude Code, Windsurf, and Codex from one tool
- **Centralized Rules**: Store all your AI assistant rules in one place, sync to unlimited projects
- **Automatic Sync**: Update rules once, propagate changes to all projects instantly
- **Multi-Target Projects**: Install rules for multiple AI assistants in the same project (e.g., Cursor + Augment)
- **Status Tracking**: See which projects have outdated rules, conflicts, or local modifications
- **Symlinks or Copies**: Choose between automatic updates (symlinks) or project-specific customization (copies)

### Custom Commands for AI Assistants

- **Slash Commands**: Manage custom `/commands` for Augment, Claude, and Codex
- **Command Library**: Pre-built commands for code review, testing, refactoring, and API design
- **Sync Commands**: Keep custom commands consistent across all your projects
- **Target-Specific**: Install commands only to assistants that support them

### Team Collaboration & Sharing

- **GitHub Packages**: Share rules and commands with your team via GitHub repositories
- **Version Control**: Track package versions, check for updates, view diffs before updating
- **Smart Discovery**: Search and install rules/commands by name across all packages
- **Team Standards**: Enforce consistent AI coding practices across your organization

### Advanced Features

- **Global Configuration**: Install system-wide configs for Claude Code CLI, Windsurf, and Codex
- **Conflict Detection**: Three-way merge detection (source changed, user modified, or both)
- **Change Tracking**: See exactly what changed before updating rules
- **Flexible Installation**: Install rules only, commands only, or both together
- **Git Integration**: Full git submodule support for package management

## Installation

### Option 1: Install as a System Command (Recommended)

1. Clone this repository:

   ```bash
   git clone <repository-url> agent-warden
   cd agent-warden
   ```

2. Install using pip (this makes `warden` available system-wide):

   ```bash
   pip install -e .
   ```

3. Verify installation:

   ```bash
   warden --help
   ```

### Option 2: Run Directly

1. Clone this repository
2. Ensure Python 3.8+ is installed
3. Run directly:

   ```bash
   python3 warden.py --help
   ```

### Updating Agent Warden

#### Automatic Updates (Default)

Agent Warden automatically checks for updates once per day and applies them after your command completes successfully. This ensures you always have the latest features and bug fixes without manual intervention.

**How it works:**
- Checks for updates once per day when you run any command
- Shows a notification if updates are available
- Applies updates automatically after your command completes
- Handles both repository and system-wide installations
- Skips updates if git working directory has uncommitted changes
- Fails gracefully on network errors without interrupting your work

**Disable automatic updates:**

```bash
warden config --auto-update false
```

**Re-enable automatic updates:**

```bash
warden config --auto-update true
```

#### Manual Updates

If you prefer to update manually or have disabled automatic updates:

```bash
cd agent-warden
git pull --rebase
# The warden command will automatically use the updated code
```

For system-wide installations, you may need to reinstall after pulling:

```bash
cd agent-warden
git pull --rebase
pip install -e .
```

## Initial Setup

After installation, Agent Warden automatically:

1. Creates configuration and state files in the installation directory
2. Initializes directories for rules, commands, and packages
3. Loads the included `mdc.mdc` meta-rule file

## Usage

### Install Rules and Commands to Projects

**Important**: The built-in `mdc.mdc` file is a meta-rule that defines the MDC format itself. It's not meant for project installation. Use package rules or commands instead.

```bash
# Install rules to a new project
warden install /path/to/project --target augment --rules coding-no-emoji git-commit

# Install with custom name
warden install /path/to/app --name my-project --rules coding-no-emoji

# Add rules to existing project (no need to specify path/target again!)
warden install --project my-project --rules git-commit

# Add commands to existing project
warden install --project my-project --commands code-review test-gen

# Install both rules and commands to new project
warden install /path/to/project --rules coding-no-emoji --commands code-review

# Install with file copies instead of symlinks
warden install /path/to/project --copy --rules coding-no-emoji

# Install package rules
warden install /path/to/project --rules owner/repo:typescript
```

### Project Management

```bash
# List all registered projects
warden project list

# Show detailed project information
warden project my-project

# Configure default targets (avoid repeating --target)
warden project configure my-project --targets augment cursor claude
# Now adding rules without --target applies to all configured targets!

# Update ALL projects with outdated rules/commands (skips conflicts)
warden project update

# Preview what would be updated across all projects
warden project update --dry-run

# Update a specific project (all outdated rules/commands)
warden project update my-project

# Update specific rules in a project
warden project update my-project --rules coding-no-emoji git-commit

# Update specific commands in a project
warden project update my-project --commands code-review

# Preview what would be updated in a project
warden project update my-project --dry-run

# Force update conflicts without prompting
warden project update my-project --force

# Rename a project
warden project rename old-name new-name

# Remove a project from tracking
warden project remove my-project

# Convert symlinks to copies for project-specific modifications
warden project sever my-project

# Sever only a specific target in a multi-target project
warden project sever my-project --target cursor

# Update only a specific target in a multi-target project
warden project update my-project --target augment
```

### Multi-Target Projects

Agent Warden supports installing rules and commands for multiple AI assistants in the same project. Each target is managed independently:

```bash
# Install to multiple targets at once
warden install /path/to/project --target cursor,augment --rules coding-no-emoji

# Or configure default targets for a project
warden project configure my-project --targets cursor augment claude

# Now installations apply to all configured targets
warden install --project my-project --rules git-commit
# Installs to cursor, augment, and claude

# Each target can have different rules
warden install --project my-project --target cursor --rules cursor-specific-rule
warden install --project my-project --target augment --rules augment-specific-rule

# Update only one target
warden project update my-project --target cursor

# Sever only one target (others remain as symlinks)
warden project sever my-project --target augment

# Check status shows all targets
warden status
```

**Multi-Target Behavior:**
- Each target stores its own files independently (`.cursor/rules/`, `.augment/rules/`, etc.)
- Severing one target doesn't affect others
- You can have different rules installed for different targets
- Updates can be applied to all targets or specific ones
- Storage: Each target maintains its own copies/symlinks

### Manage Commands

```bash
# List all available commands
warden list-commands

# Get detailed information about a command
warden list-commands --info code-review

# List projects with detailed command information
warden project list --verbose
```

### GitHub Package Management

```bash
# Add a GitHub package
warden add-package username/repo-name

# Add a specific version/branch
warden add-package username/repo-name@v1.0.0
warden add-package username/repo-name@main

# List installed packages
warden list-packages

# Check for updates
warden check-updates

# View changes before updating
warden check-updates --diff username/repo-name

# Update a package
warden update-package username/repo-name

# Search across all packages
warden search api-design
```

### System-wide Configuration

```bash
# Install global configuration for Claude Code CLI
warden global-install claude

# Install global configuration for Windsurf
warden global-install windsurf

# Force overwrite existing global configuration
warden global-install codex --force
```

### Project Status

```bash
# Check status of all projects
warden status

# Check status of specific project
warden status my-project

# Show differences between source and installed files for a specific rule/command
warden diff my-project coding-no-emoji
warden diff my-project code-review
```

### Configuration

Customize Agent Warden behavior with the config command:

```bash
# View current configuration
warden config --show

# Set default target (used when --target is not specified)
warden config --set-default-target augment

# Enable/disable remote project updates in global commands
warden config --update-remote false

# Enable/disable automatic updates of Agent Warden
warden config --auto-update false

# Now installations will use augment by default
warden install /path/to/project --rules coding-no-emoji
```

**Configuration options:**

- **Default Target**: Set your preferred AI tool (cursor, augment, claude, windsurf, codex)
- **Update Remote Projects**: Enable/disable updating remote projects in global `update` and `status` commands (default: true)
- **Auto Update**: Enable/disable automatic updates of Agent Warden itself (default: true)
- Configuration is saved to `.warden_config.json` (already in .gitignore)
- Default target is `augment` if not configured

## Supported AI Tools and Targets

The script supports multiple AI development tools with their specific configurations:

### Project-level Targets

- **cursor**: Rules in `.cursor/rules/`, commands in `.cursor/rules/` (rules-based system)
- **augment**: Rules in `.augment/rules/`, commands in `.augment/commands/` (default)
- **claude**: Rules in `.claude/rules/`, commands in `.claude/commands/`
- **windsurf**: Rules in `.windsurf/rules/`, commands in `.windsurf/commands/`
- **codex**: Rules in `.codex/rules/`, commands in `.codex/commands/`

### System-wide Configurations

- **Claude Code CLI**: `~/.claude/CLAUDE.md` (with rules in `~/.claude/warden-rules.md`)
- **Windsurf**: `~/.codeium/windsurf/memories/global_rules.md`
- **Codex**: `~/.codex/config.toml`

### Command Support

- **Full Command Support**: Augment, Claude, Codex
- **Rules Only**: Cursor, Windsurf (uses global rules)

## File Structure

```
agent-warden/
├── warden.py               # Main script
├── fs_backend.py           # File system backend (local and remote SSH)
├── mdc.mdc                 # Meta-rule defining MDC format (not for projects)
├── rules/                  # Built-in rules directory
│   ├── coding-no-emoji.mdc # No emojis in code rule
│   ├── git-commit.mdc      # Git commit standards
│   ├── documentation.mdc   # Documentation standards
│   └── example/            # Example rules subdirectory (optional)
├── commands/               # Built-in commands directory
│   ├── code-review.md      # Code review command
│   ├── test-gen.md         # Test generation command
│   ├── refactor.md         # Refactoring command
│   ├── api-design.md       # API design command
│   └── example/            # Example commands subdirectory (optional)
├── packages/               # Downloaded GitHub packages (gitignored)
│   └── .gitkeep            # Keeps directory in git
├── .warden_config.json     # Configuration file (gitignored)
├── .warden_state.json      # State tracking file (gitignored)
├── tests/                  # Test suite
├── pyproject.toml          # Python package configuration
├── update-warden.sh        # Update script
└── README.md               # This documentation

Notes:
- Built-in rules and commands are in the root rules/ and commands/ directories
- User-created rules and commands can be added to these directories
- The packages/ directory and all its contents are gitignored
- Configuration and state files are gitignored
```

## Available Commands

The tool includes several pre-built command templates:

### 🔍 code-review

Perform comprehensive code reviews with security, performance, and best practices analysis.

- **Usage**: `/code-review [file-path]`
- **Features**: Security analysis, performance review, code quality assessment
- **Tags**: review, security, performance, best-practices

### 🧪 test-gen

Generate comprehensive unit tests for functions, classes, or modules.

- **Usage**: `/test-gen [file-path|function-name]`
- **Features**: Multiple test frameworks, edge cases, mocking strategies
- **Tags**: testing, unit-tests, tdd, quality-assurance

### 🔧 refactor

Suggest and implement code refactoring improvements for better maintainability.

- **Usage**: `/refactor [file-path|selection]`
- **Features**: Code smell detection, design patterns, performance improvements
- **Tags**: refactoring, code-quality, maintainability, clean-code

### 🌐 api-design

Design and document RESTful APIs with best practices and OpenAPI specifications.

- **Usage**: `/api-design [resource-name|endpoint-path]`
- **Features**: OpenAPI specs, authentication, error handling, pagination
- **Tags**: api, rest, openapi, design, documentation

## GitHub Package Management

Agent Warden supports downloading and managing packages from GitHub repositories, making it easy to share and distribute custom rules and commands across teams and projects.

### Package Structure

A valid Agent Warden package repository should have the following structure:

```
your-warden-package/
├── rules/                  # Optional: Project-specific MDC rules
│   ├── typescript.mdc      # TypeScript-specific rules
│   ├── python.mdc          # Python-specific rules
│   └── security.mdc        # Security-focused rules
├── commands/               # Optional: Custom commands
│   ├── deploy.md           # Deployment command
│   ├── test-e2e.md         # E2E testing command
│   └── lint-fix.md         # Linting and fixing command
├── warden.json             # Optional: Package metadata
└── README.md               # Package documentation
```

**Note**: Package rules should be actual project rules, not meta-rules that define the MDC format itself.

### Package Installation

```bash
# Install a package from GitHub
warden add-package myteam/warden-rules

# Install a specific version
warden add-package myteam/warden-rules@v2.1.0

# Install from a specific branch
warden add-package myteam/warden-rules@development
```

### Using Package Content

Once installed, you can use package content in your projects:

```bash
# Install built-in commands
warden install /path/to/project --commands code-review test-gen

# Install package commands (using package:command syntax)
warden install /path/to/project --commands myteam/warden-rules:deploy myteam/warden-rules:test-e2e

# Mix built-in and package commands
warden install /path/to/project --commands code-review myteam/warden-rules:deploy
```

### Version Management

```bash
# Check which packages have updates available
warden check-updates

# View changes before updating
warden check-updates --diff myteam/warden-rules --files

# Update to latest version
warden update-package myteam/warden-rules

# Update to specific version
warden update-package myteam/warden-rules --ref v2.2.0
```

### Package Discovery

```bash
# Search for commands across all packages
warden search deploy

# List all packages with status
warden list-packages --status
```

## Installation Types

### Symlinks (Default)

- **Pros**: Automatic updates when central rules/commands change
- **Cons**: Cannot make project-specific modifications
- **Use case**: Projects that should always use the latest rules and commands
- **Supported targets**: Cursor, Claude, Windsurf, Codex

### Copies

- **Pros**: Can be modified for project-specific needs
- **Cons**: Must be manually updated
- **Use case**: Projects requiring customized rules or commands
- **Required for**: Augment (does not support symlinks), Remote installations (via SSH)

### Target-Specific Behavior

**Augment**: Always uses copies, even if you don't specify `--copy`. This is because Augment's file watching system doesn't follow symlinks. The tool will automatically use copy mode and notify you:

```bash
warden install /path/to/project --target augment --rules coding-no-emoji
# Output: [INFO] Augment target requires file copies (symlinks not supported)
```

**Remote installations**: Always use copies regardless of target, since symlinks cannot span SSH connections.

## State Management

The script maintains state in `.warden_state.json` with information about:

- Project name and path
- Target configuration used
- Installation type (symlink or copy)
- Last update timestamp

## Error Handling

The script provides comprehensive error handling for:

- Invalid project paths
- Permission issues
- File operation failures
- Missing projects or configurations

## Examples

### Basic Workflow

```bash
# Install rules and commands to an Augment project
warden install ~/projects/my-app --target augment --rules coding-no-emoji --commands code-review

# Install only specific commands to a Cursor project (omit --rules to skip rules)
warden install ~/projects/cursor-app --target cursor --commands code-review

# List all projects with detailed information
warden project list --verbose

# Later, convert to copy for customization
warden project sever my-app

# Update the project with latest rules and commands
warden project update my-app
```

### Advanced Workflows

```bash
# Set up global configuration for Claude Code CLI
warden global-install claude

# Install comprehensive development setup
warden install ~/projects/api-project --target augment --commands api-design test-gen code-review

# Install rules-only setup for Windsurf (uses global rules)
warden install ~/projects/windsurf-project --target windsurf

# Check available commands and their details
warden list-commands
warden list-commands --info refactor
```

### Package Management Workflow

```bash
# Add team's custom package
warden add-package myteam/warden-devops@v1.0.0

# Check what's available
warden list-packages --status
warden search deploy

# Install project with team's custom commands
warden install ~/projects/api-service --target augment --commands \
  code-review myteam/warden-devops:deploy myteam/warden-devops:monitor

# Later, check for updates
warden check-updates
warden check-updates --diff myteam/warden-devops --files

# Update when ready
warden update-package myteam/warden-devops
```

### Multi-Tool Setup

Agent Warden now supports installing the same rules to multiple AI tools (targets) in the same project! This allows you to use Cursor, Augment, Claude, and other tools simultaneously with the same rules.

```bash
# Install to multiple AI tools for the same project
# First installation creates the project
warden install ~/projects/multi-tool-app --target augment --rules coding-no-emoji
# Second installation adds cursor target to the same project
warden install ~/projects/multi-tool-app --target cursor --rules coding-no-emoji
# Third installation adds claude target
warden install ~/projects/multi-tool-app --target claude --rules coding-no-emoji --commands api-design

# Configure default targets (so you don't have to specify --target every time)
warden project configure multi-tool-app --targets augment cursor claude

# Now adding rules applies to all configured default targets automatically!
warden install --project multi-tool-app --rules git-commit
# ^ Installs to augment, cursor, AND claude

# Add rules to a specific target only (overrides defaults)
warden install --project multi-tool-app --rules typescript --target augment

# Update all default targets
warden project update multi-tool-app

# Update a specific target
warden project update multi-tool-app --target cursor

# Sever (convert symlinks to copies) for a specific target
warden project sever multi-tool-app --target cursor

# Set up global configurations
warden global-install claude
warden global-install windsurf
warden global-install codex
```

**Key Features:**

- Install the same project with multiple targets (e.g., both Augment and Cursor)
- Configure default targets to avoid repeating --target flags
- Each target maintains its own rules and commands
- Add rules to all default targets or specific targets
- Update and manage targets independently
- Full backward compatibility with existing single-target projects

## Troubleshooting

### Permission Errors

Ensure you have read/write permissions for:

- The project directories
- The target installation directories

### Symlink Issues

On some systems, symlink creation may require elevated permissions or specific filesystem support.

### Debug Mode

Set the `DEBUG` environment variable to see detailed error traces:

```bash
DEBUG=1 warden install /path/to/project
```

## Development Setup

Agent Warden has no runtime dependencies (pure Python standard library), but development requires some tools.

### Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-rules.git
cd agent-rules

# Run the setup script (macOS/Linux)
./setup-dev.sh
```

The setup script will:

- Check Python version
- Create virtual environment in `.venv/`
- Install all development dependencies
- Install git hooks for code quality enforcement
- Run tests to verify setup (on fresh setup only)
- Activate the virtual environment

### Manual Setup

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Development Dependencies

The `requirements-dev.txt` includes:

- **pytest** - Testing framework
- **pytest-cov** - Test coverage
- **pytest-mock** - Mocking support
- **ruff** - Fast Python linter and formatter
- **black** - Code formatter
- **mypy** - Static type checker

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=warden --cov-report=html

# Run specific test file
pytest tests/test_rename.py

# Run with verbose output
pytest -v
```

For detailed testing information, including manual testing with isolated environments, see [tests/README.md](tests/README.md).

### Code Quality

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code with black
black .

# Type checking with mypy
mypy warden.py
```

### Git Hooks

Git hooks are automatically installed by `setup-dev.sh` to enforce code quality:

**Pre-commit hook** runs before each commit:

- Ruff linter checks (must pass)
- All tests (must pass)

```bash
# Install hooks manually
./install-hooks.sh

# Bypass hooks in emergencies (not recommended)
git commit --no-verify
```

The hooks ensure that all commits maintain code quality and don't break tests.

### Project Structure

```
agent-rules/
├── warden.py           # Main script
├── rules/                 # Built-in MDC rules
│   ├── coding-no-emoji.mdc
│   └── git-commit.mdc
├── commands/              # Built-in commands
│   ├── code-review.md
│   ├── test-gen.md
│   └── ...
├── packages/              # Installed GitHub packages
├── tests/                 # Test suite
│   ├── conftest.py
│   ├── test_rename.py
│   └── ...
├── requirements-dev.txt   # Development dependencies
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Set up development environment (see Development Setup above)
4. Make your changes
5. Run tests and linters (`pytest && ruff check .`)
6. Commit your changes following git-commit rules (see `rules/git-commit.mdc`)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Submit a pull request

## License

This project is open source. Please check the repository for license details.

---

## Keywords & Search Terms

**AI Coding Assistants:** Cursor, Augment, Claude Code, Windsurf, Codex, GitHub Copilot, AI pair programming

**Rules Management:** cursor rules, augment rules, claude rules, .cursor/rules, .augment/rules, .claude/rules, AI assistant configuration, coding rules manager, rules synchronization

**Commands Management:** custom commands, slash commands, AI commands, augment commands, claude commands

**Use Cases:** manage AI rules across projects, sync cursor rules, centralized rules management, AI assistant configuration tool, team AI standards, enterprise AI coding practices

**Related:** MDC rules, markdown documentation convention, AI coding standards, cursor rules manager, augment configuration, claude configuration, multi-project AI setup
