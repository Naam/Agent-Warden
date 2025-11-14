---
description: Design and document RESTful APIs with best practices and OpenAPI specifications
argument-hint: [resource-name|endpoint-path]
tags: ["api", "rest", "openapi", "design", "documentation"]
---

# API Design Command

Design comprehensive RESTful APIs following industry best practices, including endpoint structure, request/response formats, authentication, and OpenAPI documentation.

## API Design Principles

### 1. RESTful Design
- **Resource-based URLs**: Nouns, not verbs
- **HTTP Methods**: Proper verb usage (GET, POST, PUT, DELETE, PATCH)
- **Status Codes**: Meaningful HTTP response codes
- **Stateless**: Each request contains all necessary information

### 2. URL Structure
- **Hierarchical**: Logical resource relationships
- **Consistent**: Predictable naming patterns
- **Versioned**: API version management
- **Filterable**: Query parameters for filtering/sorting

### 3. Data Formats
- **JSON**: Primary data exchange format
- **Consistent Structure**: Standardized response formats
- **Error Handling**: Structured error responses
- **Pagination**: Large dataset handling

## Design Process

### 1. Resource Identification
```
Resources: Users, Posts, Comments, Categories
Relationships: User -> Posts -> Comments
```

### 2. Endpoint Design
```
GET    /api/v1/users              # List users
POST   /api/v1/users              # Create user
GET    /api/v1/users/{id}         # Get user
PUT    /api/v1/users/{id}         # Update user
DELETE /api/v1/users/{id}         # Delete user
GET    /api/v1/users/{id}/posts   # Get user's posts
```

### 3. Request/Response Design
```json
// POST /api/v1/users
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}

// Response: 201 Created
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Output Format

Generate complete API specification including:

### 1. OpenAPI Specification
```yaml
openapi: 3.0.3
info:
  title: User Management API
  version: 1.0.0
  description: API for managing users and their resources

paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
                  pagination:
                    $ref: '#/components/schemas/Pagination'
```

### 2. Implementation Guidelines
```python
# Example Flask implementation
@app.route('/api/v1/users', methods=['GET'])
def list_users():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    users = User.query.paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        'data': [user.to_dict() for user in users.items],
        'pagination': {
            'page': page,
            'pages': users.pages,
            'total': users.total,
            'has_next': users.has_next,
            'has_prev': users.has_prev
        }
    })
```

## Usage Examples

```bash
# Design API for a resource
/api-design User

# Design specific endpoint
/api-design /api/v1/users/{id}/posts

# Generate OpenAPI spec
/api-design --format openapi User

# Include authentication
/api-design --auth jwt User
```

## Features Included

### 1. Authentication & Authorization
- **JWT Tokens**: Stateless authentication
- **API Keys**: Service-to-service auth
- **OAuth 2.0**: Third-party integration
- **Role-based Access**: Permission management

### 2. Error Handling
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### 3. Pagination & Filtering
```
GET /api/v1/users?page=2&limit=50&sort=created_at&order=desc&filter[role]=admin
```

### 4. Rate Limiting
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Configuration Options

- `--format <openapi|postman|insomnia>`: Output format
- `--auth <jwt|apikey|oauth>`: Authentication method
- `--version <v1|v2>`: API version
- `--database <sql|nosql>`: Database considerations
- `--framework <flask|fastapi|express>`: Implementation framework

## Best Practices Applied

### 1. Consistency
- Uniform naming conventions
- Consistent response structures
- Standard error formats
- Predictable behavior patterns

### 2. Security
- Input validation
- Output sanitization
- Authentication requirements
- Rate limiting implementation

### 3. Performance
- Efficient pagination
- Caching strategies
- Compression support
- Optimized queries

## Related Commands

- `/test-gen`: Generate API tests
- `/security-scan`: API security analysis
- `/performance-test`: Load testing scenarios
- `/documentation`: Generate API documentation
