# XBRL-US MCP Server

[![smithery badge](https://smithery.ai/badge/@hamid-vakilzadeh/xbrl-us-mcp)](https://smithery.ai/server/@hamid-vakilzadeh/xbrl-us-mcp)

A Model Context Protocol (MCP) server that provides secure access to XBRL-US financial data with session-based authentication and state persistence.

## Features

- **Session-Based Authentication**: Efficient session management with automatic token reuse
- **State Persistence**: XBRL instances persist across multiple tool calls within the same session
- **Company Search**: Search for companies by fiscal year and retrieve financial facts
- **Secure Credentials**: SHA256-hashed credential validation and secure storage

## Tools Available

### Search Companies

Search for companies by fiscal year and retrieve financial facts.

- **Parameters**:
  - `year` (integer): Fiscal year to search for
  - `limit` (optional, default: 10): Maximum number of results to return
- **Returns**: List of financial facts for companies in the specified year

## Authentication

This server requires XBRL-US API credentials provided via URL parameters:

- **Username**: Your XBRL-US account username
- **Password**: Your XBRL-US account password
- **Client ID**: Your XBRL-US API client ID
- **Client Secret**: Your XBRL-US API client secret

### Configuration Format

Credentials are passed as a base64-encoded JSON object in the `config` URL parameter:

```bash
# Example configuration object (before base64 encoding):
{
  "username": "your-xbrl-username",
  "password": "your-xbrl-password",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret"
}
```

## Installation & Setup

### Prerequisites

- Python 3.13+
- XBRL-US API account and credentials
- uv (for dependency management)

### Local Development

1. Clone the repository:

```bash
git clone <repository-url>
cd xbrl-us-mcp
```

2. Install dependencies:

```bash
uv sync
```

3. Run the server:

```bash
uv run playground
```

The server will start on port 8081 by default and open smithery.ai playground

## Usage Example

### Search for Companies in 2023

```
Tool: search_companies
Parameters: {"year": 2023, "limit": 10}
```

This will return financial facts for companies with data available for fiscal year 2023.

## Architecture

### Session Management

The server implements sophisticated session management:

- **FastMCP Session IDs**: Uses FastMCP's built-in session identification
- **Session-Scoped Storage**: XBRL instances persist across requests within the same session
- **Automatic Token Reuse**: Reuses valid XBRL authentication tokens to improve performance
- **Credential Validation**: SHA256 hashing ensures secure credential comparison
- **Token Expiration**: Automatically handles expired tokens and re-authenticates when needed

### Project Structure

```
xbrl-us-mcp/
├── src/
│   ├── index.py              # Main FastMCP server
│   └── funcs/
│       ├── __init__.py
│       └── middleware.py     # Session authentication middleware
├── smithery.yaml             # Deployment configuration
├── pyproject.toml           # Python dependencies
└── README.md               # This file
```

## Session Persistence Benefits

- **Performance**: Eliminates redundant authentication calls
- **Efficiency**: Reuses XBRL instances across multiple tool calls
- **Reliability**: Handles token expiration gracefully
- **Security**: Secure credential hashing and validation

## Expected Behavior

**First Request in Session:**

```
New XBRL instance created for session abc123...: token...
```

**Subsequent Requests in Same Session:**

```
Reusing valid XBRL session for abc123...
Reusing XBRL instance: token...
```

## Error Handling

The server provides detailed error messages for:

- Missing or invalid credentials
- Authentication failures
- Token expiration
- Network connectivity issues
- Invalid search parameters

## Security Features

- **Credential Hashing**: SHA256 hashing of credentials for secure comparison
- **Session Isolation**: Each session maintains independent authentication state
- **Token Validation**: Automatic validation of XBRL token expiration
- **Secure Storage**: Credentials are never stored in plain text

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.