# Git Hooks for Agent Warden

This directory contains git hooks that help maintain code quality and prevent accidental automated actions.

## Available Hooks

### Pre-Commit Hook

**Purpose:** Ensures code quality before allowing commits

**Checks:**
- Ruff linter (code quality and style)
- Pytest (all tests must pass)

**Usage:**
```bash
# Automatically runs on every commit
git commit -m "Your message"

# Bypass in emergencies (not recommended)
git commit --no-verify -m "Emergency fix"
```

### Pre-Push Hook

**Purpose:** Prevents automated pushes to the `main` branch

**Why?** This hook ensures that only human users push to the main branch, preventing AI assistants/agents from accidentally pushing code to main without user review. Feature branches can be pushed freely.

**Behavior:**
- Blocks pushes to `main` or `master` branches with a clear message
- Allows pushes to feature branches (e.g., `feature/my-feature`, `bugfix/issue-123`)
- Provides guidance for AI assistants on what to do instead
- Instructs users on how to push manually

**For AI Assistants/LLMs/Agents:**

When you encounter this hook, you should:

1. **DO:** Create and push feature branches freely
2. **DO:** Inform the user when changes to main are ready to push
3. **DO:** Ask if the user wants to review changes before pushing to main
4. **DO:** Let the user decide when to push to main

Example workflow:
```
# You CAN do this:
git checkout -b feature/add-remote-support
git commit -m "Add remote SSH support"
git push origin feature/add-remote-support

# You CANNOT do this (will be blocked):
git checkout main
git commit -m "Add remote SSH support"
git push origin main  # BLOCKED
```

Example message when on main:
```
I've committed the changes to main. The code is ready to be pushed.
Would you like to review the changes before pushing to main?

Alternatively, I can create a feature branch and push that instead.
```

**What NOT to do:**
- Don't attempt to push to main/master branch
- Don't try to bypass the hook with `--no-verify`
- Don't suggest removing or disabling the hook
- Don't try to modify the hook

**For Human Users:**

The hook only blocks pushes to `main`/`master`. Feature branches work normally:

```bash
# Feature branches work fine (no blocking)
git checkout -b feature/my-feature
git push origin feature/my-feature  # Allowed

# Pushing to main is blocked
git checkout main
git push origin main  # Blocked by hook
```

To push to main after the hook blocks:

```bash
# Option 1: Push manually (recommended)
git push

# Option 2: Bypass the hook (not recommended)
git push --no-verify

# Option 3: Remove the hook (if you don't want this protection)
rm .git/hooks/pre-push
```

## Installation

Install all hooks:

```bash
./install-hooks.sh
```

This will:
1. Copy hooks from `hooks/` to `.git/hooks/`
2. Make them executable
3. Display confirmation message

## Manual Installation

If you prefer to install hooks manually:

```bash
# Install pre-commit hook
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Install pre-push hook
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Disabling Hooks

### Temporarily (for one commit/push)

```bash
# Skip pre-commit checks
git commit --no-verify -m "Message"

# Skip pre-push check
git push --no-verify
```

### Permanently

```bash
# Remove pre-commit hook
rm .git/hooks/pre-commit

# Remove pre-push hook
rm .git/hooks/pre-push

# Remove all hooks
rm .git/hooks/*
```

## Hook Details

### Pre-Commit Hook Features

- **Stash Management:** Automatically stashes unstaged changes before running checks
- **Merge/Rebase Detection:** Skips checks during merge/rebase operations
- **Clear Error Messages:** Shows exactly what failed and how to fix it
- **Automatic Cleanup:** Restores stashed changes after checks complete

### Pre-Push Hook Features

- **Branch-Aware:** Only blocks pushes to `main`/`master`, allows feature branches
- **Clear Visual Feedback:** Uses box drawing characters for visibility
- **Targeted Messaging:** Separate instructions for AI assistants and human users
- **Example Messages:** Shows AI assistants exactly what to say
- **Multiple Options:** Gives users several ways to proceed

## Why These Hooks?

### Pre-Commit Hook

**Benefits:**
- Catches code quality issues before they enter the repository
- Ensures all tests pass before committing
- Maintains consistent code style
- Prevents broken commits

**Trade-offs:**
- Adds time to each commit (typically 1-5 seconds)
- Can be bypassed with `--no-verify` if needed

### Pre-Push Hook

**Benefits:**
- Prevents accidental automated pushes to main by AI assistants
- Allows AI assistants to push feature branches freely
- Gives users control over when code is pushed to main
- Allows for final review before merging to main
- Protects main branch from unintended changes
- Encourages feature branch workflow

**Trade-offs:**
- Requires manual push action for main branch
- Can be bypassed with `--no-verify` if needed

## Best Practices

1. **Don't Bypass Hooks Regularly**
   - Hooks are there for a reason
   - Only use `--no-verify` in genuine emergencies

2. **Keep Hooks Updated**
   - Re-run `./install-hooks.sh` after pulling updates
   - Hooks in the repository may be improved over time

3. **Understand What Hooks Do**
   - Read the hook scripts to understand their behavior
   - Modify them if your workflow requires different checks

4. **For AI Assistants**
   - Always respect the pre-push hook for main branch
   - Feel free to push feature branches
   - Never suggest bypassing the hook
   - Always ask the user before pushing to main

## Troubleshooting

### Pre-Commit Hook Fails

```bash
# See what failed
git commit -m "Message"

# Fix ruff issues automatically
ruff check --fix .

# Run tests to see failures
pytest

# After fixing, commit again
git commit -m "Message"
```

### Pre-Push Hook Blocks Push

This is expected behavior! The hook is working correctly.

```bash
# Review your changes
git log
git diff origin/main

# When ready, push manually
git push
```

### Hooks Not Running

```bash
# Check if hooks are installed
ls -la .git/hooks/

# Reinstall hooks
./install-hooks.sh

# Check if hooks are executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

## Contributing

If you improve these hooks, please:
1. Test them thoroughly
2. Update this README
3. Commit the changes to the `hooks/` directory
4. Ask users to re-run `./install-hooks.sh`

