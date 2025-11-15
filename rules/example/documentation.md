---
description: Guidelines for handling documentation files - avoid creating new docs unless explicitly requested, prefer chat summaries and updating existing files
globs: ["**/*.md", "**/*.mdx", "**/README*", "**/CHANGELOG*", "**/CONTRIBUTING*", "**/*.rst", "**/*.adoc"]
alwaysApply: true
type: always_apply
---

# Documentation File Guidelines

## Core Principles

- **Communication**: Use the chat interface for all progress updates, summaries, and implementation explanations
- **Existing First**: Always search for and update existing documentation before considering new files
- **User Consent**: Require explicit user permission before creating any new documentation file
- **Minimal Docs**: Only create documentation when absolutely necessary and requested

## Rules

### 1. Never Create Unsolicited Documentation

**Severity**: Error

**Rationale**: Creating documentation files without user request clutters the workspace and may not align with project documentation standards.

Do NOT create documentation files such as:

- README.md files
- CHANGELOG.md files
- API documentation
- Implementation guides
- Architecture documents
- Tutorial files
- Any other .md, .mdx, .rst, or .adoc files

Unless the user explicitly requests them.

### 2. Prefer Chat for Communication

**Severity**: Error

**Rationale**: Chat is the appropriate medium for progress updates and summaries during development.

Use the chat interface to:

- Report progress on tasks
- Summarize implementation details
- Explain architectural decisions
- Provide usage examples
- Document changes made
- Share next steps

### 3. Update Existing Documentation First

**Severity**: Error

**Rationale**: Existing documentation should be kept up-to-date rather than creating redundant new files.

When documentation is needed:

1. Search for existing documentation files using codebase-retrieval
2. Read the existing files thoroughly
3. Update and improve existing content
4. Only consider new files if no relevant documentation exists

### 4. Confirm Before Creating New Files

**Severity**: Error

**Rationale**: User should have control over what documentation files are added to their project.

If creating a new documentation file seems necessary:

1. Explain to the user why a new file is needed
2. Suggest the file name and location
3. Provide a brief outline of the proposed content
4. Wait for explicit user confirmation
5. Only proceed after receiving approval

## Examples

### ❌ Bad

**Creating README without being asked:**

```
User: "I just implemented a new feature"
Agent: *creates README.md documenting the feature*
```

**Creating documentation to summarize work:**

```
Agent: *creates IMPLEMENTATION.md to document changes made*
```

### ✅ Good

**Providing summary in chat:**

```
User: "I just implemented a new feature"
Agent: "I've completed the feature implementation. Here's a summary: [details in chat]"
```

**Asking before creating documentation:**

```
Agent: "I notice there's no API documentation for this module. Would you like me to create an API.md file documenting the public interfaces?"
User: "Yes, please"
Agent: *creates API.md*
```

**Updating existing documentation:**

```
Agent: "I found an existing README.md. I'll update it to include the new feature documentation."
```

## Workflow

When documentation is needed:

1. Check if user explicitly requested documentation
2. If not requested, use chat to communicate instead
3. If documentation seems necessary, search for existing files
4. If existing files found, update them
5. If no existing files and new file seems warranted, ask user for confirmation
6. Only create new file after receiving explicit approval
