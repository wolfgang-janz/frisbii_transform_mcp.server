# OAuth2 Configuration for Frisbii Transform MCP

This document explains how to configure OAuth2 authentication for the Frisbii Transform MCP server.

## Authentication Methods

The MCP server supports two authentication methods:

1. **Bearer Token Authentication** (original method)
2. **OAuth2 Client Credentials Flow** (new method)

The server automatically detects which method to use based on the environment variables provided.

## OAuth2 Configuration

### Environment Variables

Configure the following environment variables in your `mcp.json` or system environment:

```json
{
  "servers": {
    "frisbii-transform": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "frisbii_transform_mcp.server"],
      "env": {
        "FRISBII_BASE_URL": "https://sandbox.billwerk.com",
        "FRISBII_OAUTH2_CLIENT_ID": "your_client_id",
        "FRISBII_OAUTH2_CLIENT_SECRET": "your_client_secret",
        "FRISBII_OAUTH2_TOKEN_URL": "https://sandbox.billwerk.com/oauth/token",
        "FRISBII_OAUTH2_SCOPE": "",
        "FRISBII_TOKEN_STORAGE": "frisbii_oauth_token.json"
      }
    }
  }
}
```


### Bearer Token Fallback

If OAuth2 credentials are not provided, the server will fall back to Bearer token authentication:

```json
{
  "env": {
    "FRISBII_API_KEY": "your_bearer_token"
  }
}
```

## OAuth2 Management Tools

The MCP server provides several tools for managing OAuth2 authentication:

### `oauth2_status`
Check the current OAuth2 configuration and token status.

Returns information about:
- Whether OAuth2 is configured
- Current authentication method
- Token existence and validity
- Token expiration time

### `oauth2_refresh_token`
Force refresh of the OAuth2 token.

This will:
- Remove the existing token file
- Request a new token from the OAuth2 provider
- Save the new token for future use

### `oauth2_clear_token`
Clear the stored OAuth2 token.

This will:
- Remove the token storage file
- Force re-authentication on the next API request

## Token Management

### Automatic Token Refresh
- Tokens are automatically refreshed when they expire
- A 60-second buffer is used before expiration to ensure validity
- Tokens are stored locally in the specified storage file

### Token Storage
- Tokens are stored in JSON format in the specified file
- The file includes access token, expiration time, and other OAuth2 metadata
- The storage file should be kept secure and not committed to version control

### Security Considerations
- Keep your client ID and client secret secure
- Add the token storage file to your `.gitignore`
- Use environment variables or secure configuration management
- Regularly rotate your OAuth2 credentials

## Production Configuration

For production use:

1. Update `FRISBII_BASE_URL` to the production endpoint
2. Use production OAuth2 credentials
3. Ensure secure storage of credentials
4. Monitor token refresh operations
5. Implement proper error handling and logging

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check that OAuth2 credentials are correctly set
2. **Token Refresh Failed**: Verify the token URL and network connectivity
3. **Invalid Credentials**: Confirm client ID and secret with Frisbii support
4. **Scope Issues**: Ensure the requested scope matches your application permissions

### Debug Steps

1. Use `oauth2_status` to check configuration
2. Try `oauth2_refresh_token` to force a new token
3. Check server logs for detailed error messages
4. Verify network connectivity to the OAuth2 endpoints

## Migration from Bearer Token

To migrate from Bearer token to OAuth2:

1. Obtain OAuth2 credentials from Frisbii
2. Update your `mcp.json` with OAuth2 environment variables
3. Remove or comment out `FRISBII_API_KEY`
4. Restart the MCP server
5. Use `oauth2_status` to verify the configuration

The server will automatically detect and use OAuth2 when the credentials are available.
