---
description: No emojis allowed in code or comments
globs: ["**/*.{ts,tsx,js,jsx,py,go,rs,java,cpp,c,h,hpp,dart}"]
alwaysApply: true
type: always_apply
---

# No Emojis in Code

**Rule**: Never use emojis anywhere in code files.

**Rationale**: Emojis in code reduce readability, cause encoding issues, and are unprofessional.

## Never use emojis in

- Variable names
- Function names
- Class names
- Comments
- String literals
- Any part of the code file

## Examples

### ❌ Bad

Emojis in function names and comments:

```python
def calculate_total_💰(items):
    total = 0  # 💵 Running total
    return total  # 🎉 Done!
```

Emojis in string literals:

```python
message = "Welcome! 🎉"
status = "✅ Success"
```

### ✅ Good

Clear, professional code without emojis:

```python
def calculate_total_price(items):
    total = 0  # Running total
    return total  # Done
```

Plain text in string literals:

```python
message = "Welcome!"
status = "Success"
```
