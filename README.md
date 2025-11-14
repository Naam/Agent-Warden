<div align="center">
  <img src="logo.jpg" alt="Agent Warden Logo" width="200"/>

# Agent Warden

  **Centralized Rules & Commands Manager for AI Coding Assistants**

  Sync Cursor Rules, Augment Rules, Claude Rules & Custom Commands Across All Your Projects

  [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

</div>

---

**Stop copying `.cursor/rules`, `.augment/rules`, and `.claude/rules` between projects!**

Agent Warden is a powerful command-line tool that manages and synchronizes AI coding assistant rules and custom commands across multiple projects. Whether you're using Cursor, Augment, Claude Code, Windsurf, or Codex, Agent Warden keeps your AI assistant configurations consistent and up-to-date.

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

# Update the rule once, sync to all projects
warden project update --all
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

## Supported AI Coding Assistants

| Assistant | Rules Support | Commands Support | Config Path |
|-----------|--------------|------------------|-------------|
| **Cursor** | ✅ `.cursor/rules/` | ❌ | Project-level |
| **Augment** | ✅ `.augment/rules/` | ✅ `.augment/commands/` | Project-level |
| **Claude Code** | ✅ `.claude/rules/` | ✅ `.claude/commands/` | Project + Global |
| **Windsurf** | ✅ `.windsurf/rules/` | ❌ | Project + Global |
| **Codex** | ✅ `.codex/rules/` | ✅ `.codex/commands/` | Project + Global |

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

- **Global Configuration**: Install system-wide configs for Claude Desktop, Windsurf, and Codex
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

If you installed with pip in editable mode (`-e`), simply pull the latest changes:

```bash
cd agent-warden
git pull --rebase
# The warden command will automatically use the updated code
```

## Initial Setup

The script automatically:

1. Downloads the MDC rules file from the specified URL
2. Initializes a git repository to track changes
3. Creates configuration and state files

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

# Update a specific project
warden project update my-project

# Update with conflicts (prompts for confirmation)
warden project update my-project

# Force update conflicts without prompting
warden project update my-project --force

# Rename a project
warden project rename old-name new-name

# Remove a project from tracking
warden project remove my-project

# Convert symlinks to copies for project-specific modifications
warden project sever my-project
```

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
# Install global configuration for Claude Desktop
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

# Show differences between source and installed files
warden diff my-project
```

### Configuration

Customize Agent Warden behavior with the config command:

```bash
# View current configuration
warden config --show

# Set default target (used when --target is not specified)
warden config --set-default-target augment

# Now installations will use augment by default
warden install /path/to/project --rules coding-no-emoji
```

**Configuration options:**

- **Default Target**: Set your preferred AI tool (cursor, augment, claude, windsurf, codex)
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

- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
- **Windsurf**: `~/.codeium/windsurf/memories/global_rules.md`
- **Codex**: `~/.codex/config.toml`

### Command Support

- **Full Command Support**: Augment, Claude, Codex
- **Rules Only**: Cursor, Windsurf (uses global rules)

## File Structure

```
agent-warden/
├── warden.py               # Main script
├── mdc.mdc                 # Meta-rule defining MDC format (not for projects)
├── rules/                  # Rules directory
│   └── example/            # Example rules (tracked in git)
│       ├── coding-no-emoji.mdc # No emojis in code rule
│       └── git-commit.mdc      # Git commit standards
├── commands/               # Commands directory
│   └── example/            # Example commands (tracked in git)
│       ├── code-review.md  # Code review command
│       ├── test-gen.md     # Test generation command
│       ├── refactor.md     # Refactoring command
│       └── api-design.md   # API design command
├── packages/               # Downloaded GitHub packages (gitignored)
│   └── .gitkeep            # Keeps directory in git
├── .warden_config.json     # Configuration file (gitignored)
├── .warden_state.json      # State tracking file (gitignored)
├── tests/                  # Test suite
├── update-warden.sh        # Update script
└── README.md               # This documentation

Notes:
- User-created rules and commands in rules/ and commands/ are gitignored
- Only the example/ subdirectories are tracked
- The packages/ directory and all its contents are gitignored
- Users have full control over packages without risking commits to the repo
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

### Copies

- **Pros**: Can be modified for project-specific needs
- **Cons**: Must be manually updated
- **Use case**: Projects requiring customized rules or commands

## State Management

The script maintains state in `.mdc_state.json` with information about:

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
warden install ~/projects/my-app --target augment --commands

# Install only specific commands to a Cursor project
warden install ~/projects/cursor-app --target cursor --no-rules --commands code-review

# List all projects with detailed information
warden list --verbose

# Later, convert to copy for customization
warden sever my-app

# Update the project with latest rules and commands
warden update my-app
```

### Advanced Workflows

```bash
# Set up global configuration for Claude Desktop
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
