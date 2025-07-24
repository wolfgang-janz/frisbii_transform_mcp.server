# Frisbii Transform MCP Server - Development Guide

This project implements a Model Context Protocol (MCP) server for the Frisbii Transform subscription and billing API.

## Project Structure

```
frisbii-transform-mcp/
├── frisbii_transform_mcp/
│   ├── __init__.py
│   └── server.py          # Main MCP server implementation
├── .vscode/
│   ├── mcp.json          # MCP server configuration
│   └── settings.json     # VS Code settings
├── pyproject.toml        # Project configuration
├── README.md            # Documentation
└── copilot-instructions.md  # This file
```

## Key Components

### Main Server (`server.py`)
- **FastMCP Integration**: Uses the FastMCP framework for MCP server implementation
- **HTTP Client**: Uses httpx for making API requests to Frisbii Transform
- **Pydantic Models**: Data validation and serialization
- **Tool Categories**:
  - Customer Management (CRUD operations)
  - Contract Management (lifecycle, pausing, resuming)
  - Component Subscriptions (usage-based billing)
  - Usage Tracking (metered usage)
  - Invoice Management
  - Payment Processing
  - Plan Management
  - Reporting
  - Webhook Management

### API Coverage
The server provides comprehensive coverage of the Frisbii Transform API including:
- 30+ MCP tools covering all major API endpoints
- Full CRUD operations for customers, contracts, subscriptions
- Advanced features like contract pausing/resuming, usage tracking
- Financial operations (payments, refunds, invoicing)
- Reporting and analytics capabilities

## Development Guidelines

### Adding New Tools
1. Define Pydantic models for request/response validation
2. Implement the tool function with proper error handling
3. Use the `@mcp.tool()` decorator
4. Add comprehensive docstrings with parameter descriptions
5. Handle HTTP errors appropriately

### Authentication
- The server uses Bearer token authentication
- Set `FRISBII_API_KEY` environment variable
- Configure `FRISBII_BASE_URL` for sandbox vs production

### Error Handling
- All API calls use `response.raise_for_status()` for HTTP error handling
- Client connection context management with `get_client()`
- Proper logging for debugging

## SDK Reference
This project is based on the MCP Python SDK: https://github.com/modelcontextprotocol/create-python-server

## Usage
The MCP server can be integrated with any MCP-compatible client to provide access to the Frisbii Transform API through natural language interactions.

## Testing
When developing new features:
1. Test with sandbox environment first
2. Verify API responses match expected schemas
3. Test error conditions and edge cases
4. Validate input parameters with Pydantic models
