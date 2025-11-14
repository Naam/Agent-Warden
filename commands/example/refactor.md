---
description: Suggest and implement code refactoring improvements for better maintainability
argument-hint: [file-path|selection]
tags: ["refactoring", "code-quality", "maintainability", "clean-code"]
---

# Refactor Command

Analyze code and suggest refactoring improvements to enhance readability, maintainability, and performance while preserving functionality.

## Refactoring Categories

### 1. Code Structure
- **Extract Method**: Break down large functions
- **Extract Class**: Separate responsibilities
- **Move Method**: Improve class organization
- **Inline Method**: Remove unnecessary abstractions

### 2. Data Organization
- **Extract Variable**: Clarify complex expressions
- **Rename Variable**: Improve naming clarity
- **Replace Magic Numbers**: Use named constants
- **Consolidate Duplicate Code**: Remove repetition

### 3. Conditional Logic
- **Replace Conditional with Polymorphism**: Use inheritance
- **Decompose Conditional**: Simplify complex conditions
- **Consolidate Conditional Expression**: Combine related conditions
- **Replace Nested Conditional with Guard Clauses**: Early returns

### 4. Method Signatures
- **Add Parameter**: Extend functionality
- **Remove Parameter**: Simplify interfaces
- **Separate Query from Modifier**: Command-query separation
- **Parameterize Method**: Reduce similar methods

## Analysis Process

### 1. Code Smells Detection
- **Long Method**: Functions doing too much
- **Large Class**: Classes with too many responsibilities
- **Duplicate Code**: Repeated logic patterns
- **Dead Code**: Unused methods or variables

### 2. Design Pattern Opportunities
- **Strategy Pattern**: Replace conditional logic
- **Factory Pattern**: Object creation abstraction
- **Observer Pattern**: Event handling
- **Decorator Pattern**: Behavior extension

### 3. Performance Improvements
- **Algorithm Optimization**: Better time complexity
- **Memory Usage**: Reduce allocations
- **Caching**: Avoid repeated calculations
- **Lazy Loading**: Defer expensive operations

## Output Format

```markdown
## Refactoring Analysis

### Current Issues
1. **Long Method** in `process_data()` (45 lines)
   - Responsibility: Data validation, transformation, and storage
   - Suggestion: Extract validation and transformation methods

2. **Duplicate Code** in `UserService` and `AdminService`
   - Common logic: Authentication and logging
   - Suggestion: Extract base service class

### Proposed Refactoring

#### 1. Extract Method Refactoring
**Before:**
```python
def process_data(self, data):
    # 45 lines of mixed responsibilities
    if not data:
        raise ValueError("Data required")
    # ... validation logic
    # ... transformation logic  
    # ... storage logic
```

**After:**
```python
def process_data(self, data):
    self._validate_data(data)
    transformed = self._transform_data(data)
    return self._store_data(transformed)

def _validate_data(self, data):
    if not data:
        raise ValueError("Data required")
    # ... validation logic

def _transform_data(self, data):
    # ... transformation logic

def _store_data(self, data):
    # ... storage logic
```

### Benefits
- Improved readability and maintainability
- Better testability of individual components
- Reduced cognitive complexity
- Enhanced reusability
```

## Usage Examples

```bash
# Refactor a specific file
/refactor src/services/user_service.py

# Refactor current selection
/refactor

# Focus on specific refactoring type
/refactor --type extract-method src/utils/data_processor.py

# Safe refactoring with tests
/refactor --with-tests src/models/user.py
```

## Refactoring Types

### Safe Refactoring
- **Rename**: Variables, methods, classes
- **Extract**: Methods, variables, constants
- **Move**: Methods between classes
- **Inline**: Temporary variables

### Behavioral Refactoring
- **Change Method Signature**: Parameters, return types
- **Replace Algorithm**: Different implementation
- **Introduce Design Pattern**: Structural changes
- **Split/Merge Classes**: Responsibility changes

## Safety Measures

### 1. Preserve Behavior
- Maintain existing functionality
- Keep public API compatibility
- Preserve error handling behavior
- Maintain performance characteristics

### 2. Testing Strategy
- Run existing tests before/after
- Generate additional tests if needed
- Verify edge cases still work
- Check integration points

### 3. Incremental Approach
- Small, focused changes
- One refactoring at a time
- Commit frequently
- Review each step

## Configuration Options

- `--type <refactoring-type>`: Focus on specific refactoring
- `--with-tests`: Include test updates
- `--safe-only`: Only safe refactorings
- `--aggressive`: Include behavioral changes
- `--preview`: Show changes without applying

## Integration Notes

Best results when:
- Comprehensive test suite exists
- Code has clear documentation
- Dependencies are well understood
- Version control is available

## Related Commands

- `/test-gen`: Generate tests for refactored code
- `/code-review`: Review refactoring quality
- `/analyze-complexity`: Measure improvement
- `/dependency-graph`: Understand code relationships
