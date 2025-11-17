# Agent Warden VHS Demo

This directory contains everything needed to record a VHS demo of Agent Warden showcasing its core workflow.

## Prerequisites

1. **Install VHS** (charmbracelet's terminal recorder):
   ```bash
   brew install vhs
   ```

2. **Install Agent Warden** (if not already installed):
   ```bash
   pip install -e .
   ```

## Demo Workflow

The demo showcases the following workflow:

1. **Show available example rules** - Display rules in `rules/example/`
2. **Copy rule from example** - Copy `coding-no-emoji.md` from `rules/example/` to `rules/`
3. **Install rule to new project** - Install to `web-app` project
4. **Check status** - Show project status and list
5. **Modify a rule** - Make changes to `coding-no-emoji.md`
6. **Check outdated status** - Show that project is now outdated
7. **Update outdated project** - Update `web-app` with latest rule
8. **Install to second project** - Install to `api-service` project
9. **Copy another rule** - Copy `git-commit.md` from example
10. **Install to ALL projects** - Install `git-commit` to all existing projects
11. **Verify final state** - Show all projects with both rules

## Quick Start

### 1. Set up the demo environment

```bash
chmod +x vhs-demo/setup-demo-env.sh
./vhs-demo/setup-demo-env.sh
```

This creates an isolated demo environment at `/tmp/warden-vhs-demo` with:
- Example rules in `rules/example/`
- Example commands in `commands/example/`
- 3 demo projects: `web-app`, `api-service`, `mobile-app`

### 2. Record the demo

```bash
vhs vhs-demo/demo.tape
```

This will:
- Execute all the commands in the tape file
- Record the terminal session
- Generate `vhs-demo/agent-warden-demo.gif`

### 3. Review the output

```bash
open vhs-demo/agent-warden-demo.gif
```

### 4. Clean up

```bash
chmod +x vhs-demo/cleanup-demo.sh
./vhs-demo/cleanup-demo.sh
```

## Customizing the Demo

### Modify the VHS Tape

Edit `vhs-demo/demo.tape` to customize:

- **Timing**: Adjust `Sleep` durations (e.g., `Sleep 2s`)
- **Typing speed**: Change `Set TypingSpeed 50ms`
- **Terminal size**: Modify `Set Width` and `Set Height`
- **Theme**: Change `Set Theme "Catppuccin Mocha"` to another theme
- **Commands**: Add, remove, or modify the command sequence

Available themes:
- `"Catppuccin Mocha"` - Soft pastels, dark (default)
- `"Dracula"` - Purple vibes
- `"nord"` - Blue/professional
- `"TokyoNight"` - Deep blue/modern
- `"Molokai"` - Classic dark
- `"GruvboxDark"` - Retro warm
- `"OneDark"` - Atom-inspired

### Test Commands Manually

Before recording, you can test the commands manually:

```bash
# Set up environment
./vhs-demo/setup-demo-env.sh

# Set WARDEN_HOME to use demo environment
export WARDEN_HOME=/tmp/warden-vhs-demo
cd /tmp/warden-vhs-demo

# Test commands
ls -la rules/example/
cp rules/example/coding-no-emoji.md rules/
warden install demo-projects/web-app --target augment --rules coding-no-emoji
warden status
# ... etc
```

### Re-record

If you need to make changes and re-record:

```bash
# Clean up previous demo
./vhs-demo/cleanup-demo.sh

# Set up fresh environment
./vhs-demo/setup-demo-env.sh

# Record again
vhs vhs-demo/demo.tape
```

## VHS Tape File Format

The `demo.tape` file uses VHS syntax:

- `Type "command"` - Types the command (simulates typing)
- `Enter` - Presses Enter key
- `Sleep 2s` - Waits for 2 seconds
- `Set <option> <value>` - Configures recording settings
- `Output <file>` - Specifies output file path

## Troubleshooting

### VHS not found

```bash
brew install vhs
```

### Warden command not found

```bash
pip install -e .
```

### Demo environment already exists

```bash
./vhs-demo/cleanup-demo.sh
./vhs-demo/setup-demo-env.sh
```

### Recording is too fast/slow

Edit `demo.tape` and adjust:
- `Set TypingSpeed 50ms` - Speed of typing simulation
- `Sleep` durations - Pauses between commands

### Output GIF is too large

Edit `demo.tape` and reduce:
- `Set Width 1200` - Terminal width
- `Set Height 800` - Terminal height

## Files

- `setup-demo-env.sh` - Creates isolated demo environment
- `demo.tape` - VHS recording script
- `cleanup-demo.sh` - Removes demo environment
- `README.md` - This file
- `agent-warden-demo.gif` - Generated output (after recording)

## Notes

- The demo uses `WARDEN_HOME=/tmp/warden-vhs-demo` to isolate from your real projects
- All demo projects and rules are temporary and can be safely deleted
- The recording is fully automated and reproducible
- You can pause and edit the tape file at any time to adjust the demo

