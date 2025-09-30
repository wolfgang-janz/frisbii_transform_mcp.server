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
- **Webhook Management**: Webhook configuration and event monitoring
- **OAuth2 Management**: Built-in authentication status and token management tools

## Installation

```bash
pip install -e .
```

## Configuration

Add this server to your MCP client configuration (e.g., Claude Desktop). Choose one of the authentication methods below:

### OAuth2 Authentication (Recommended)

```json
{
  "mcpServers": {
    "frisbii-transform": {
      "command": "python",
      "args": ["-m", "frisbii_transform_mcp.server"],
      "env": {
        "FRISBII_BASE_URL": "https://app.billwerk.com",
        "FRISBII_OAUTH2_CLIENT_ID": "your_client_id",
        "FRISBII_OAUTH2_CLIENT_SECRET": "your_client_secret",
        "FRISBII_OAUTH2_TOKEN_URL": "https://app.billwerk.com/oauth/token",
        "FRISBII_OAUTH2_SCOPE": "api"
      }
    }
  }
}
```

**Setup Requirements:**
1. Create OAuth2 client credentials in your Billwerk+ Transform settings
2. **Important:** Use dedicated client credentials - avoid sharing Admin UI credentials
3. This method provides automatic token management and refresh capabilities

### Bearer Token Authentication

```json
{
  "mcpServers": {
    "frisbii-transform": {
      "command": "python",
      "args": ["-m", "frisbii_transform_mcp.server"],
      "env": {
        "FRISBII_BASE_URL": "https://app.billwerk.com",
        "FRISBII_API_KEY": "your_api_key"
      }
    }
  }
}
```

### Optional: Legal Entity ID

For multi-entity access, add the legal entity ID to your environment configuration:

```json
"env": {
  "FRISBII_LEGAL_ENTITY_ID": "your_legal_entity_id",
  // ... other environment variables
}
```

**Note:** The `FRISBII_LEGAL_ENTITY_ID` is optional. Most single-entity Billwerk customers can omit this setting.

### Environment Endpoints

- **Production:** `https://app.billwerk.com`
- **Sandbox:** `https://sandbox.billwerk.com`

For detailed OAuth2 setup instructions, see [OAUTH2_SETUP.md](OAUTH2_SETUP.md).

## OAuth2 Management Tools

The server includes built-in tools for OAuth2 management:
- `oauth2_status`: Check authentication status, token validity, and configuration
- `oauth2_refresh_token`: Force refresh of OAuth2 tokens
- `oauth2_clear_token`: Clear stored OAuth2 tokens

## Development

This project is built using:
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP server framework
- [httpx](https://www.python-httpx.org/) for HTTP client operations
- [Pydantic](https://docs.pydantic.dev/) for data validation

## License

MIT License