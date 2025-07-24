# Frisbii Transform MCP Server

A Model Context Protocol (MCP) server that provides tools to interact with the Frisbii Transform subscription and billing API.

## Features

This MCP server provides tools for:

- **Customer Management**: Create, retrieve, update, and delete customers
- **Contract Management**: Manage subscription contracts and their lifecycle
- **Component Subscriptions**: Handle component-based subscriptions
- **Usage Tracking**: Manage metered usage data
- **Invoice Operations**: Create, retrieve, and manage invoices
- **Payment Processing**: Handle payments and refunds
- **Discount Management**: Manage discount subscriptions
- **Plan Management**: Access plan groups, plans, and plan variants
- **Report Generation**: Generate various business reports

## Installation

1. Install the required dependencies:
```bash
pip install -e .
```

2. Set up your Frisbii Transform API credentials as environment variables:

**Required Configuration**
```bash
export FRISBII_LEGAL_ENTITY_ID="your_legal_entity_id"  # Required for all requests
```

**Option 1: Bearer Token Authentication (Simple)**
```bash
export FRISBII_API_KEY="your_api_key"
export FRISBII_BASE_URL="https://sandbox.billwerk.com"  # or https://app.billwerk.com for production
```

**Option 2: OAuth2 Authentication (Recommended)**
```bash
export FRISBII_BASE_URL="https://sandbox.billwerk.com"  # or https://app.billwerk.com for production
export FRISBII_OAUTH2_CLIENT_ID="your_client_id"
export FRISBII_OAUTH2_CLIENT_SECRET="your_client_secret"
export FRISBII_OAUTH2_TOKEN_URL="https://sandbox.billwerk.com/oauth/token"
export FRISBII_OAUTH2_SCOPE="api"
```

For detailed OAuth2 setup instructions, see [OAUTH2_SETUP.md](OAUTH2_SETUP.md).

## Usage

Add this server to your MCP client configuration:

```json
{
  "servers": {
    "frisbii-transform": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "frisbii_transform_mcp.server"]
    }
  }
}
```

## API Tools

The server provides comprehensive tools for all major Frisbii Transform API endpoints including:

- Customer operations (CRUD)
- Contract lifecycle management
- Subscription management
- Usage tracking and billing
- Invoice and payment handling
- Plan and pricing management
- Reporting and analytics

## Authentication

This server supports two authentication methods and requires a legal entity ID for all requests:

### Required Configuration
The `FRISBII_LEGAL_ENTITY_ID` environment variable must be set and will be included as the `x-selected-legal-entity-id` header in all API requests.

### Bearer Token Authentication
Use Bearer token authentication with the Frisbii Transform API by setting the `FRISBII_API_KEY` environment variable with your valid API token.

### OAuth2 Authentication (Recommended)
Use OAuth2 client credentials flow by setting the appropriate OAuth2 environment variables. This method provides better security and automatic token management.

The server automatically detects which authentication method to use based on the environment variables provided. See [OAUTH2_SETUP.md](OAUTH2_SETUP.md) for detailed OAuth2 configuration instructions.

### OAuth2 Management Tools
The server includes built-in tools for OAuth2 management:
- `oauth2_status`: Check authentication status, token validity, and legal entity ID configuration
- `oauth2_refresh_token`: Force refresh of OAuth2 tokens
- `oauth2_clear_token`: Clear stored OAuth2 tokens

## Development

This project is built using:
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP server framework
- [httpx](https://www.python-httpx.org/) for HTTP client operations
- [Pydantic](https://docs.pydantic.dev/) for data validation

## License

MIT License
