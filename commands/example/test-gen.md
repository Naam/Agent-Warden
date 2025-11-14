---
description: Generate comprehensive unit tests for the specified code
argument-hint: [file-path|function-name]
tags: ["testing", "unit-tests", "tdd", "quality-assurance"]
---

# Test Generation Command

Generate comprehensive unit tests for functions, classes, or modules with proper test coverage and edge case handling.

## Test Generation Features

### 1. Test Structure
- **Setup/Teardown**: Proper test initialization and cleanup
- **Test Organization**: Logical grouping of related tests
- **Naming Conventions**: Clear, descriptive test names
- **Documentation**: Test purpose and expected behavior

### 2. Coverage Areas
- **Happy Path**: Normal operation scenarios
- **Edge Cases**: Boundary conditions and limits
- **Error Conditions**: Exception handling and error states
- **Integration Points**: External dependencies and interactions

### 3. Test Types
- **Unit Tests**: Individual function/method testing
- **Integration Tests**: Component interaction testing
- **Property Tests**: Property-based testing where applicable
- **Parameterized Tests**: Multiple input scenarios

### 4. Mocking Strategy
- **External Dependencies**: API calls, database connections
- **File System**: File operations and I/O
- **Time-dependent Code**: Date/time operations
- **Random Operations**: Deterministic test execution

## Output Format

Generate tests in the appropriate testing framework:

```python
# Example Python unittest output
import unittest
from unittest.mock import Mock, patch
from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.instance = YourClass()
    
    def test_method_happy_path(self):
        """Test normal operation of method."""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = self.instance.method("input")
        
        # Assert
        self.assertEqual(result, expected)
    
    def test_method_edge_case(self):
        """Test edge case handling."""
        with self.assertRaises(ValueError):
            self.instance.method(None)
```

## Usage Examples

```bash
# Generate tests for a specific file
/test-gen src/utils/helpers.py

# Generate tests for a specific function
/test-gen calculate_total

# Generate tests with specific framework
/test-gen --framework pytest src/models/user.py

# Generate integration tests
/test-gen --type integration src/api/endpoints.py
```

## Framework Support

### Python
- **unittest**: Standard library testing framework
- **pytest**: Popular third-party testing framework
- **doctest**: Documentation-based testing

### JavaScript/TypeScript
- **Jest**: Popular testing framework
- **Mocha**: Flexible testing framework
- **Vitest**: Fast unit testing framework

### Other Languages
- **JUnit**: Java testing framework
- **RSpec**: Ruby testing framework
- **Go testing**: Built-in Go testing package

## Configuration Options

- `--framework <name>`: Specify testing framework
- `--type <unit|integration|e2e>`: Test type to generate
- `--coverage-target <percentage>`: Target coverage percentage
- `--mock-external`: Automatically mock external dependencies
- `--include-fixtures`: Generate test data fixtures

## Best Practices Applied

### Test Quality
- **AAA Pattern**: Arrange, Act, Assert structure
- **Single Responsibility**: One assertion per test
- **Descriptive Names**: Clear test method names
- **Independent Tests**: No test dependencies

### Coverage Strategy
- **Branch Coverage**: All code paths tested
- **Boundary Testing**: Edge cases and limits
- **Error Scenarios**: Exception handling
- **State Verification**: Object state validation

## Integration Notes

Works best with:
- Clear function/class documentation
- Type hints or annotations
- Existing code structure understanding
- Access to dependency information

## Related Commands

- `/code-review`: Review generated tests for quality
- `/coverage-report`: Analyze test coverage
- `/refactor`: Improve testability of code
- `/mock-setup`: Generate mock configurations
