"""
XBRL-US MCP Server
A FastMCP server that provides access to XBRL-US financial data with authentication
"""

import logging
from fastmcp import FastMCP
from fastmcp.server.context import Context
from xbrl_us import XBRL
from smithery.decorators import smithery
from pandas import DataFrame
from typing import Annotated, Literal
from pydantic import Field
import requests
from funcs.middleware import SessionAuthMiddleware, ConfigSchema


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@smithery.server(config_schema=ConfigSchema)
def create_server():
    # Initialize the FastMCP server with configuration schema support
    mcp = FastMCP("XBRL-US Data Server")
    mcp.add_middleware(SessionAuthMiddleware())

    @mcp.tool(
        annotations={
            "title": "Query XBRL Data",
            "readOnlyHint": True,
            "openWorldHint": True,
            "idempotentHint": True,
        },
        exclude_args=["ctx"],
    )
    async def query(
        endpoint: Annotated[
            str,
            Field(
                description="The XBRL-US API endpoint path (e.g., '/fact/search', '/entity/search', '/report/search'). See meta endpoints for available options.",
                examples=["/fact/search", "/entity/search", "/report/search"],
            ),
        ],
        fields: Annotated[
            list[str],
            Field(
                description="List of field names to retrieve from the endpoint. Must not be empty.",
                min_length=1,
                examples=[["entity.name", "fact.value", "period.instant"]],
            ),
        ],
        parameters: Annotated[
            dict[str, str | int | float | bool | list] | None,
            Field(
                description="Optional dictionary of query parameters to filter results (e.g., {'entity.ticker': 'AAPL', 'period.fiscal-year': 2023})",
                default=None,
                examples=[{"entity.ticker": "AAPL", "period.fiscal-year": 2023}],
            ),
        ] = None,
        sort: Annotated[
            dict[str, Literal["desc", "asc"]] | None,
            Field(
                description="Optional dictionary specifying sort order for fields. Keys are field names, values are 'desc' or 'asc'",
                default=None,
                examples=[{"period.instant": "desc", "fact.value": "asc"}],
            ),
        ] = None,
        unique: Annotated[
            bool,
            Field(
                description="Whether to return only unique/distinct results, removing duplicates",
                default=False,
            ),
        ] = False,
        limit: Annotated[
            int,
            Field(
                description="Maximum number of results to return. Must be between 1 and 2000",
                ge=1,
                le=2000,
                default=100,
            ),
        ] = 100,
        ctx: Context = None,
    ) -> DataFrame:
        """Query XBRL-US API endpoints for financial data and facts

        This tool provides flexible access to XBRL-US data by allowing queries to various
        API endpoints with customizable fields, filters, and sorting options.

        Returns:
            DataFrame containing the requested XBRL data with specified fields

        Raises:
            ValueError: If XBRL authentication is not configured or fields are not provided
            ValueError: If the API request fails
        """
        xbrl: XBRL = ctx.get_state("xbrl")

        if xbrl is None:
            raise ValueError(
                "XBRL authentication required. Please provide valid credentials in the request."
            )

        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        if not fields:
            raise ValueError("fields are required")

        try:
            return xbrl.query(
                endpoint=endpoint,
                fields=fields,
                parameters=parameters,
                limit=limit,
                unique=unique,
                sort=sort,
            )
        except Exception as e:
            raise ValueError(f"Failed to fetch XBRL data: {e}")

    @mcp.tool(
        annotations={
            "title": "Get XBRL Endpoint Metadata",
            "readOnlyHint": True,
            "openWorldHint": True,
            "idempotentHint": True,
        },
        exclude_args=["ctx"],
    )
    async def list_xbrl_endpoints(
        endpoint: Annotated[
            Literal[
                "meta",
                "meta/assertion",
                "meta/concept",
                "meta/cube",
                "meta/document",
                "meta/dts",
                "meta/dts/concept",
                "meta/dts/network",
                "meta/entity",
                "meta/entity/report",
                "meta/fact",
                "meta/label",
                "meta/network",
                "meta/network/relationship",
                "meta/relationship",
                "meta/report",
                "meta/report/fact",
                "meta/report/network",
            ],
            Field(
                description="The XBRL-US metadata endpoint to query. Use 'meta' for general metadata or specific paths like 'meta/concept' for concept definitions",
                examples=["meta", "meta/concept", "meta/entity"],
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """List available XBRL API endpoints

        Args:
            endpoint: The XBRL-US API endpoint to query
            ctx: FastMCP context object containing XBRL authentication state

        Returns:
            Response from the XBRL API endpoint

        Raises:
            ValueError: If XBRL authentication is not configured
        """
        xbrl: XBRL = ctx.get_state("xbrl")

        if xbrl is None:
            raise ValueError(
                "XBRL authentication required. Please provide valid credentials in the request."
            )

        response = requests.get(
            url=f"https://api.xbrl.us/api/v1/{endpoint}",
            headers={"Authorization": f"Bearer {xbrl.access_token}"},
        )
        response.raise_for_status()
        return response.json()

    return mcp
