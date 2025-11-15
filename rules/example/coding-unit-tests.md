---
description: Behavior-driven testing principles - validate correct behavior, not implementation details
globs: ["**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/*_test.go", "**/*Test.java", "**/*Tests.cs"]
alwaysApply: false
type: agent_requested
---

# Unit Testing Standards

## Core Principles

Tests are **executable specifications** that define what code SHOULD do:

- Validate correct behavior, not current implementation
- Catch bugs and regressions when behavior deviates
- Test observable outcomes through public APIs
- Remain valid when implementation changes

## Key Rules

### 1. Test Behavior, Not Implementation

❌ **Bad - Mirrors implementation:**

```javascript
test('calculateDiscount', () => {
  expect(calculateDiscount(100, true)).toBe(100 * 0.9); // Repeats formula
});
```

[ ] **Good - Validates requirement:**

```javascript
test('VIP customers receive 10% discount', () => {
  expect(calculateDiscount(100, true)).toBe(90);
});
```

### 2. Cover Edge Cases

Test boundary conditions, error handling, and failure modes:

```javascript
test('divide by zero throws error', () => {
  expect(() => divide(10, 0)).toThrow('Division by zero');
});
```

### 3. Use Descriptive Test Names

Test names should explain the requirement:

```javascript
test('email addresses without @ symbol should fail validation', () => {
  expect(validateEmail('invalid.email.com')).toBe(false);
});
```

### 4. Avoid Implementation Coupling

- Test through public APIs only
- Don't access private methods or properties
- Don't assert on internal state
- Allow implementation to change freely

## Quick Checklist

- [ ] Test validates expected behavior, not implementation
- [ ] Test name describes the requirement clearly
- [ ] Test would fail if implementation is incorrect
- [ ] Test uses meaningful assertions
- [ ] Test covers edge cases and error conditions
- [ ] Test is resilient to refactoring
