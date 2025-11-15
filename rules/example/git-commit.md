---
description: Enforce state-of-the-art git commit message principles with strict quality standards, pre-commit hook enforcement, and professional tone requirements
globs: ["**/*"]
alwaysApply: true
type: always_apply
---

# Git Commit Message Standards

## Core Principles

- **Quality First**: Apply state-of-the-art git commit message principles
- **No Bypassing**: Strictly prohibit bypassing pre-commit hooks
- **Professional Tone**: Maintain factual, objective language without exaggeration or emojis
- **Atomic Commits**: Each commit should contain a single, logical change
- **Test Before Commit**: Always validate tests pass before creating commits
- **No Remote Push**: AI assistant must never push commits to remote repository
- **Selective Staging**: Never use `git add -A` or `git add .` - stage files explicitly

## Commit Message Structure

### Subject Line (First Line)

- **Length**: 50 characters or less (hard limit: 72)
- **Mood**: Imperative (command form)
- **Capitalization**: First letter capitalized
- **Punctuation**: No period at the end
- **Clarity**: Clear, concise description of the change

**Examples:**

```
Add user authentication feature
Fix memory leak in data processor
Refactor database connection logic
Update API documentation for v2.0
Remove deprecated payment methods
```

**Avoid:**

```
❌ Added user authentication (past tense)
❌ Adding user authentication (present continuous)
❌ add user authentication (not capitalized)
❌ Add user authentication. (period at end)
❌ Add user auth 🎉 (emoji)
```

### Body (Optional but Recommended)

- **Separation**: Blank line between subject and body
- **Line Wrap**: 72 characters per line
- **Focus**: Explain WHAT and WHY, not HOW
- **Tone**: Factual and objective

**Example:**

```
Add user authentication feature

Users need to securely access their accounts. This change
implements JWT-based authentication with refresh tokens.

The implementation includes:
- Login and registration endpoints
- Token validation middleware
- Password hashing with bcrypt
```

## Strict Prohibitions

### 1. Never Bypass Pre-commit Hooks

**Prohibited commands:**

```bash
❌ git commit --no-verify
❌ git commit -n
❌ git commit -m "message" --no-verify
```

**Rationale**: Pre-commit hooks ensure code quality, security, and consistency.

### 2. No Emojis in Commit Messages

**Never use emojis** in:

- Subject lines
- Body text
- Any part of commit messages

**Rationale**: Emojis reduce professionalism, cause encoding issues, and complicate parsing.

### 3. No Bulk Git Add

**Prohibited commands:**

```bash
❌ git add -A
❌ git add .
❌ git add --all
```

**Instead, stage files explicitly:**

```bash
✅ git add src/auth.py
✅ git add tests/test_auth.py
✅ git add src/models/user.py tests/test_user.py
```

**Rationale**: Explicit staging ensures you review each change and maintain atomic commits.

### 4. No Remote Push by AI

**The AI assistant must NEVER:**

- Push commits to remote repository
- Execute `git push` commands
- Force push with `git push --force`

**Rationale**: User should review and control what gets pushed to remote.

## Atomic Commits

Each commit should contain a **single, logical change**:

✅ **Good (Atomic):**

```
Commit 1: Add user model
Commit 2: Add user authentication endpoints
Commit 3: Add authentication tests
```

❌ **Bad (Non-Atomic):**

```
Commit 1: Add user model, authentication, tests, and fix unrelated bug
```

## Professional Tone

### Use Factual, Objective Language

✅ **Good:**

```
Fix null pointer exception in payment processor
Improve query performance by adding database index
Update dependencies to address security vulnerabilities
```

❌ **Bad:**

```
Fix terrible bug that was breaking everything
Massively improve performance with amazing optimization
Update deps (no explanation)
```

### Avoid

- Exaggeration ("massive", "huge", "amazing")
- Vague terms ("fix stuff", "update things")
- Informal language ("oops", "whoops")
- Emojis and special characters
- Unnecessary exclamation marks

## Test Validation Required

**Before creating any commit:**

1. Run relevant tests
2. Verify all tests pass
3. Fix any failing tests
4. Only then create the commit

**Never commit:**

- Failing tests
- Broken code
- Untested changes (for non-trivial changes)

## Workflow

1. Make changes to code
2. Run tests and verify they pass
3. Stage files explicitly: `git add <specific-files>`
4. Write commit message following standards
5. Create commit (hooks will run automatically)
6. If hooks fail, fix issues and try again
7. **Do not push** - let user review and push

## Examples

### Example 1: Feature Addition

```
Add password reset functionality

Users need ability to reset forgotten passwords. This change
implements a secure password reset flow using time-limited
tokens sent via email.

Changes include:
- Password reset request endpoint
- Token generation and validation
- Email notification service integration
- Reset password form and endpoint
```

### Example 2: Bug Fix

```
Fix race condition in cache invalidation

Cache was occasionally serving stale data due to race condition
between read and invalidation operations. Added mutex lock to
ensure atomic cache operations.

Fixes #1234
```

### Example 3: Refactoring

```
Extract payment processing into separate service

Payment logic was tightly coupled with order processing, making
it difficult to test and maintain. Extracted into dedicated
PaymentService class with clear interface.

No functional changes - pure refactoring.
```
