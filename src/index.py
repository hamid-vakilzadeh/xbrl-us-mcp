"""
XBRL-US MCP Server
A FastMCP server that provides access to XBRL-US financial data with authentication
"""

import logging
from fastmcp import FastMCP
from fastmcp.server.context import Context
from xbrl_us import XBRL

from funcs.middleware import (
    SessionAuthMiddleware,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastMCP server with configuration schema support
mcp = FastMCP("XBRL-US Data Server")
mcp.add_middleware(SessionAuthMiddleware())


@mcp.tool(
    annotations={
        "title": "Search Companies",
        "description": "Search for companies by name or ticker symbol",
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
async def search_companies(
    year: int, limit: int = 10, ctx: Context = None
) -> list[dict]:
    """Search for companies by name or ticker symbol

    Args:
        year: Fiscal year to search for
        limit: Maximum number of results to return (default: 10)

    Returns:
        Formatted list of matching companies with CIK and ticker information
    """
    xbrl: XBRL = ctx.get_state("xbrl")

    if xbrl is None:
        raise ValueError(
            "XBRL authentication required. Please provide valid credentials in the request."
        )

    try:
        return xbrl.fact(
            endpoint="/fact/search",
            fields=["fact.*"],
            parameters={"period_fiscal_year": year, "entity_cik": "0000320193"},
            limit=limit,
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch XBRL data: {e}")


if __name__ == "__main__":
    # Run the server
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8081,
        path="/mcp",
        stateless_http=False,
        log_level="WARNING",
    )
