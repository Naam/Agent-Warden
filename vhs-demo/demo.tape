# VHS Demo Tape for Agent Warden
# This tape demonstrates the core workflow of Agent Warden
#
# FEATURES:
# - Human-like typing: Variable speed (30-50ms) for natural feel
# - Progress indicators: Step counters [1/11] through [11/11]
# - Clear ending marker: Shows when demo completes and will loop
# - 20px padding: Better visual appearance
#
# CUSTOMIZATION TIPS:
# - Change Theme: "Dracula", "nord", "TokyoNight", "Molokai", "GruvboxDark", "OneDark"
# - Change Size: Width 1000-1400, Height 600-900
# - Change FontSize: 12 (small), 14 (medium), 16-18 (large)
# - Adjust Sleep times: 500ms, 1s, 2s, 3s
# See VHS-CUSTOMIZATION.md for full guide

# Output settings
Output vhs-demo/agent-warden-demo.gif
Set FontSize 14
Set FontFamily "JetBrainsMono Nerd Font"
Set Width 1200
Set Height 800
Set Padding 20
Set TypingSpeed 40ms
Set Theme "Catppuccin Mocha"
Set PlaybackSpeed 1.0
Set Shell "zsh"
# Set LoopOffset 100%    # Uncomment to play once without looping

# Source zsh configuration to get all the colors and aliases
Hide
Type "source ~/.zshrc"
Enter
Sleep 500ms
Type "clear"
Enter
Show

# Start with a clean slate
Set TypingSpeed 38ms
Type "echo '# Agent Warden Demo - Centralized Rules Manager for AI Coding Assistants' > /dev/null"
Enter
Sleep 2s
Set TypingSpeed 42ms
Type "export WARDEN_HOME=/tmp/warden-demo"
Enter
Set TypingSpeed 35ms
Type "cd /tmp/warden-demo"
Enter
Sleep 1s

# Show the initial structure
Set TypingSpeed 40ms
Type "echo '# [1/11] Show available example rules' > /dev/null"
Enter
Set TypingSpeed 33ms
Type "ls -la rules/example/"
Enter
Sleep 2s

# Copy a rule from example to rules directory
Set TypingSpeed 45ms
Type "echo '# [2/11] Copy coding-no-emoji rule from example to make it available' > /dev/null"
Enter
Set TypingSpeed 37ms
Type "cp rules/example/coding-no-emoji.md rules/"
Enter
Set TypingSpeed 41ms
Type "ls -la rules/"
Enter
Sleep 2s

# Install the rule to a new project
Set TypingSpeed 44ms
Type "echo '# [3/11] Install rule to a new project (web-app)' > /dev/null"
Enter
Set TypingSpeed 36ms
Type "warden install demo-projects/web-app --target augment --rules coding-no-emoji"
Enter
Sleep 2s

# Check status of all projects
Set TypingSpeed 39ms
Type "echo '# [4/11] Check status of all projects' > /dev/null"
Enter
Set TypingSpeed 32ms
Type "warden status"
Enter
Sleep 2s
Set TypingSpeed 43ms
Type "warden project list"
Enter
Sleep 2s

# Make a change to the rule
Set TypingSpeed 40ms
Type "echo '# [5/11] Make a change to the coding-no-emoji rule' > /dev/null"
Enter
Set TypingSpeed 34ms
Type "echo '' >> rules/coding-no-emoji.md"
Enter
Set TypingSpeed 46ms
Type "echo '## Additional Note' >> rules/coding-no-emoji.md"
Enter
Set TypingSpeed 38ms
Type "echo 'Emojis reduce code professionalism.' >> rules/coding-no-emoji.md"
Enter
Sleep 1s

# Check status to see outdated project
Set TypingSpeed 41ms
Type "echo '# [6/11] Check status - should show web-app as outdated' > /dev/null"
Enter
Set TypingSpeed 35ms
Type "warden status"
Enter
Sleep 2s

# Update the outdated project
Set TypingSpeed 44ms
Type "echo '# [7/11] Update the outdated project' > /dev/null"
Enter
Set TypingSpeed 37ms
Type "warden project update web-app"
Enter
Sleep 2s
Set TypingSpeed 40ms
Type "warden status"
Enter
Sleep 2s

# Install another project
Set TypingSpeed 43ms
Type "echo '# [8/11] Install rule to a second project (api-service)' > /dev/null"
Enter
Set TypingSpeed 36ms
Type "warden install demo-projects/api-service --target augment --rules coding-no-emoji"
Enter
Sleep 2s

# Copy and install a new rule to ALL projects
Set TypingSpeed 39ms
Type "echo '# [9/11] Copy git-commit rule from example' > /dev/null"
Enter
Set TypingSpeed 33ms
Type "cp rules/example/git-commit.md rules/"
Enter
Sleep 1s

Set TypingSpeed 45ms
Type "echo '# [10/11] Install git-commit rule to ALL existing projects at once!' > /dev/null"
Enter
Set TypingSpeed 37ms
Type "warden --yes install --rules git-commit"
Enter
Sleep 3s

# Final status check
Set TypingSpeed 40ms
Type "echo '# [11/11] Verify all projects have both rules' > /dev/null"
Enter
Set TypingSpeed 34ms
Type "warden project list"
Enter
Sleep 2s
Set TypingSpeed 42ms
Type "warden status"
Enter
Sleep 2s

# Show final state with clear ending
Type "clear"
Enter
Type "echo '# ============================================================' > /dev/null"
Enter
Type "echo '# DEMO COMPLETE!' > /dev/null"
Enter
Type "echo '# ============================================================' > /dev/null"
Enter
Type "echo '# All projects now have coding-no-emoji and git-commit rules' > /dev/null"
Enter
Type "echo '#' > /dev/null"
Enter
Type "echo '# Agent Warden - Centralized Rules Manager for AI Assistants' > /dev/null"
Enter
Type "echo '# Recording will loop - this is the end of the demo' > /dev/null"
Enter
Type "echo '# ============================================================' > /dev/null"
Enter
Sleep 5s

