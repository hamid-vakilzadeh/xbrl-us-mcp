# XBRL-US MCP Server

A Model Context Protocol (MCP) server that provides secure access to XBRL-US financial data and SEC filings. Built with FastMCP and designed for deployment on Smithery.

## Features

- **Secure Authentication**: Uses Smithery's configuration system to securely handle XBRL-US credentials
- **Company Search**: Search for companies by name or ticker symbol
- **Financial Facts**: Retrieve detailed financial facts with filtering by concept and year
- **XBRL Concepts**: Search and explore XBRL taxonomy concepts
- **SEC Filings**: Access company SEC filings with filtering options
- **Resource Access**: Provides XBRL taxonomy information as resources

## Tools Available

### 1. Search Companies

Search for companies by name or ticker symbol.

- **Parameters**: `query` (string), `limit` (optional, default: 10)
- **Returns**: Formatted list of companies with CIK and ticker information

### 2. Get Company Financial Facts

Retrieve financial facts for a specific company.

- **Parameters**: `cik` (string), `concept` (optional), `year` (optional), `limit` (optional, default: 50)
- **Returns**: Detailed financial facts data

### 3. Search XBRL Concepts

Search for XBRL taxonomy concepts.

- **Parameters**: `query` (string), `limit` (optional, default: 20)
- **Returns**: List of matching XBRL concepts with descriptions

### 4. Get Company Filings

Retrieve SEC filings for a specific company.

- **Parameters**: `cik` (string), `form_type` (optional), `year` (optional), `limit` (optional, default: 10)
- **Returns**: List of SEC filings with details

## Resources Available

### US-GAAP Taxonomy Information

- **URI**: `xbrl://taxonomies/us-gaap`
- **Description**: Provides information about common US-GAAP taxonomy concepts

## Authentication

This server requires XBRL-US API credentials:

- **Username**: Your XBRL-US account username
- **Password**: Your XBRL-US account password
- **Client ID**: Your XBRL-US API client ID
- **Client Secret**: Your XBRL-US API client secret

### Smithery Deployment

When deployed on Smithery, users provide credentials through the secure configuration interface:

```yaml
# Configuration schema (handled automatically by Smithery)
username: "your-xbrl-username"
password: "your-xbrl-password"
client_id: "your-client-id"
client_secret: "your-client-secret"
```

### Local Development

For local development, set environment variables:

```bash
export XBRL_USERNAME="your-username"
export XBRL_PASSWORD="your-password"
export XBRL_CLIENT_ID="your-client-id"
export XBRL_CLIENT_SECRET="your-client-secret"
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

3. Set environment variables (see Authentication section above)

4. Run the server:

```bash
uv run python -m src.index
```

The server will start on port 8000 by default.

### Docker Deployment

1. Build the Docker image:

```bash
docker build -t xbrl-us-mcp .
```

2. Run the container:

```bash
docker run -p 8000:8000 \
  -e XBRL_USERNAME="your-username" \
  -e XBRL_PASSWORD="your-password" \
  -e XBRL_CLIENT_ID="your-client-id" \
  -e XBRL_CLIENT_SECRET="your-client-secret" \
  xbrl-us-mcp
```

### Smithery Deployment

1. Ensure you have the Smithery CLI installed:

```bash
npm install -g @smithery/cli
```

2. Deploy to Smithery:

```bash
smithery deploy
```

The server will be available through Smithery's platform with the secure configuration interface.

## Usage Examples

### Search for Apple Inc.

```
Tool: search_companies
Parameters: {"query": "Apple", "limit": 5}
```

### Get Apple's Financial Facts for 2023

```
Tool: get_company_facts
Parameters: {"cik": "0000320193", "year": 2023, "limit": 20}
```

### Search for Revenue-related Concepts

```
Tool: search_concepts
Parameters: {"query": "Revenue", "limit": 10}
```

### Get Apple's Recent 10-K Filings

```
Tool: get_company_filings
Parameters: {"cik": "0000320193", "form_type": "10-K", "limit": 5}
```

## Project Structure

```
xbrl-us-mcp/
├── src/
│   ├── index.py              # Main FastMCP server
│   ├── utils/
│   │   ├── __init__.py
│   │   └── xbrl_client.py    # XBRL-US API client
│   └── funcs/
│       ├── __init__.py
│       └── utils.py          # Utility functions
├── smithery.yaml             # Smithery deployment config
├── Dockerfile               # Container configuration
├── pyproject.toml           # Python dependencies
└── README.md               # This file
```

## Security Features

- **Credential Protection**: All credentials are handled securely through Smithery's configuration system
- **Input Validation**: All inputs are validated before processing
- **Error Handling**: Comprehensive error handling with informative messages
- **Logging**: Structured logging for monitoring and debugging

## API Rate Limits

This server respects XBRL-US API rate limits. The XBRL-US API has usage limits based on your subscription plan. Please refer to your XBRL-US account for specific rate limit information.

## Error Handling

The server provides detailed error messages for common issues:

- Authentication failures
- Invalid CIK formats
- API rate limit exceeded
- Network connectivity issues
- Invalid search parameters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues related to:

- **XBRL-US API**: Contact XBRL-US support
- **Smithery Platform**: Contact Smithery support
- **This MCP Server**: Create an issue in this repository

## Changelog

### v0.1.0

- Initial release
- Basic XBRL-US API integration
- Smithery deployment support
- Company search, financial facts, concepts, and filings tools
- Secure authentication handling
