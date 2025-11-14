---
description: Perform a comprehensive code review with security, performance, and best practices analysis
argument-hint: [file-path]
tags: ["review", "security", "performance", "best-practices"]
---

# Code Review Command

Perform a thorough code review of the specified file or current selection, focusing on:

## Review Areas

### 1. Code Quality
- **Readability**: Clear variable names, proper formatting, logical structure
- **Maintainability**: Modular design, proper separation of concerns
- **Documentation**: Adequate comments and docstrings
- **Consistency**: Follows project coding standards

### 2. Security Analysis
- **Input validation**: Check for proper sanitization and validation
- **Authentication/Authorization**: Verify access controls
- **Data handling**: Secure storage and transmission practices
- **Vulnerability patterns**: Common security anti-patterns

### 3. Performance Considerations
- **Algorithm efficiency**: Time and space complexity analysis
- **Resource usage**: Memory leaks, unnecessary allocations
- **Database queries**: N+1 problems, indexing opportunities
- **Caching strategies**: Appropriate use of caching

### 4. Best Practices
- **Error handling**: Proper exception management
- **Testing**: Testability and test coverage considerations
- **Dependencies**: Appropriate use of external libraries
- **Design patterns**: Proper application of design patterns

## Output Format

Provide feedback in the following structure:

```
## Summary
Brief overview of the code quality and main findings.

## Issues Found
### High Priority
- Critical issues that need immediate attention

### Medium Priority  
- Important improvements that should be addressed

### Low Priority
- Minor suggestions and optimizations

## Recommendations
- Specific actionable improvements
- Code examples where helpful
- Links to relevant documentation or best practices

## Positive Aspects
- What the code does well
- Good practices to maintain
```

## Usage Examples

```bash
# Review a specific file
/code-review src/auth/login.py

# Review current selection
/code-review

# Review with focus on security
/code-review --focus security src/api/endpoints.py
```

## Configuration

You can customize the review focus by specifying areas:
- `--focus security`: Emphasize security analysis
- `--focus performance`: Focus on performance optimization
- `--focus maintainability`: Prioritize code maintainability
- `--focus all`: Comprehensive review (default)

## Integration Notes

This command works best when:
- Code context is available in the current workspace
- Project documentation and coding standards are accessible
- Test files are available for reference
- Dependencies and architecture are understood

## Related Commands

- `/test-coverage`: Analyze test coverage for the reviewed code
- `/refactor`: Suggest refactoring opportunities
- `/security-scan`: Deep security analysis
- `/performance-profile`: Detailed performance analysis
