---
description: Initialize agent context by reading and familiarizing with project rules
argument-hint:
tags: ["initialization", "context", "rules", "setup"]
---

# Initialize Context Command

**IMPORTANT**: Before proceeding with any work in this project, you MUST read and familiarize yourself with all project-specific rules and guidelines.

## Instructions

### Step 1: Read All Rule Files

Read **every file** in the following directory:

```
{{RULES_DIR}}
```

### Step 2: Internalize the Rules

For each rule file you read:

- Understand the purpose and scope of the rule
- Identify all requirements and constraints
- Note any examples or patterns to follow/avoid
- Recognize priority levels (if specified)
- Understand how rules interact with each other

### Step 3: Confirm and Report

After reading all rules, provide a report in this format:

```markdown
## ✅ Context Initialization Complete

### Rules Loaded
1. **[Rule File Name]** - [Brief description of what this rule covers]
2. **[Rule File Name]** - [Brief description of what this rule covers]
[... list all rules ...]

### Summary
- **Total Rules**: [number]
- **Key Themes**: [main categories or themes across rules]
- **Critical Requirements**: [any must-follow requirements]

### Status
✅ All rules have been read and internalized
✅ Ready to proceed with rule-compliant work
```

## When to Use This Command

Run this command:

- **At the start of every new session** with this project
- After project rules have been updated
- Before performing any significant work
- When you need to refresh your understanding of project guidelines

## What Happens Next

After successfully loading the rules:

- All your responses and code will comply with the loaded rules
- You will apply these rules during code review, refactoring, and generation
- You will reference specific rules when making recommendations
- You will flag any conflicts between requests and established rules

## Platform-Specific Notes

{{PLATFORM_NOTES}}

---

**Remember**: The rules in `{{RULES_DIR}}` are the source of truth for this project. Always prioritize these rules over general best practices when there's a conflict.
