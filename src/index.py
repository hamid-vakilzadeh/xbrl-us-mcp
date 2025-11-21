"""
XBRL-US MCP Server
A FastMCP server that provides access to XBRL-US financial data with authentication
"""

import logging
import json
from pathlib import Path
from fastmcp import FastMCP, Context
from xbrl_us import XBRL
from pandas import DataFrame
from typing import Annotated, Literal, Any
from pydantic import Field
import requests
from funcs.middleware import SessionAuthMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_and_convert_parameters(
    parameters: dict[str, Any] | str | None,
) -> dict[str, Any] | None:
    """
    Validate and convert parameters to the correct format.

    This function handles cases where the LLM passes parameters as a JSON string
    instead of a dict object, which can happen due to serialization.

    Args:
        parameters: Either a dict, JSON string, or None

    Returns:
        A validated dict or None

    Raises:
        ValueError: If parameters cannot be parsed or are in invalid format
    """
    if parameters is None:
        return None

    # If it's already a dict, return it
    if isinstance(parameters, dict):
        return parameters

    # If it's a string, try to parse it as JSON
    if isinstance(parameters, str):
        try:
            parsed = json.loads(parameters)
            if not isinstance(parsed, dict):
                raise ValueError(
                    f"Parameters must be a dictionary/object, not {type(parsed).__name__}. "
                    f"Example: {{'entity.ticker': 'AAPL', 'period.fiscal-year': 2023}}"
                )
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in parameters string: {e}. "
                f"Parameters must be a valid JSON object like {{'entity.ticker': 'AAPL', 'period.fiscal-year': 2023}}"
            ) from e

    # Invalid type
    raise ValueError(
        f"Parameters must be a dict/object or JSON string, got {type(parameters).__name__}. "
        f"Example: {{'entity.ticker': 'AAPL', 'period.fiscal-year': 2023}}"
    )


# Initialize the FastMCP server with configuration schema support
mcp = FastMCP(
    name="XBRL-US Data Server",
    middleware=[SessionAuthMiddleware()],
)


@mcp.custom_route("/.well-known/mcp-config", methods=["GET"])
async def well_known_config(request: Request) -> JSONResponse:
    """
    Serve the MCP configuration schema at the well-known endpoint.
    This allows clients to discover the configuration options for this server.
    """
    # Read the config schema from the .well-known directory
    config_path = Path(__file__).parent.parent / ".well-known" / "mcp-config"

    try:
        with open(config_path, "r") as f:
            config_schema = json.load(f)
        return JSONResponse(
            content=config_schema,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )
    except FileNotFoundError:
        logger.error(f"Configuration schema file not found at {config_path}")
        return JSONResponse(
            content={"error": "Configuration schema not found"}, status_code=404
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration schema: {e}")
        return JSONResponse(
            content={"error": "Invalid configuration schema"}, status_code=500
        )


@mcp.tool(
    annotations={
        "title": "Query XBRL Data",
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True,
    },
    # exclude_args=["ctx"],
)
async def query(
    ctx: Context,
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
        dict[str, str | int | float | bool | list] | str | None,
        Field(
            description="Query parameters to filter results. Must be a JSON object/dict with key-value pairs. Example: {'entity.ticker': 'AAPL', 'period.fiscal-year': 2023}",
            default=None,
            examples=[
                {"entity.ticker": "AAPL", "period.fiscal-year": 2023},
                {"entity.ticker": "MSFT", "report.document-type": "10-K"},
            ],
        ),
    ] = None,
    sort: Annotated[
        dict[str, Literal["desc", "asc"]] | str | None,
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

    # Validate and convert parameters if provided
    try:
        validated_parameters = validate_and_convert_parameters(parameters)
    except ValueError as e:
        raise ValueError(
            f"Parameter validation failed: {e}\n\n"
            f"IMPORTANT: Parameters must be provided as a JSON object/dict, not a string.\n"
            f"Correct format: {{'entity.ticker': 'AAPL', 'period.fiscal-year': 2023}}\n"
            f"NOT as a string: '{{'entity.ticker': 'AAPL'}}'"
        ) from e

    try:
        validated_sort = validate_and_convert_parameters(sort)
    except ValueError as e:
        raise ValueError(
            f"Sort validation failed: {e}\n\n"
            f"IMPORTANT: Sort must be provided as a JSON object/dict, not a string.\n"
            f"Correct format: {{'entity.ticker': 'DESC', 'period.fiscal-year': 'ASC'}}\n"
            f"NOT as a string: '{{'entity.ticker': 'AAPL'}}'"
        ) from e

    # Create a retry decorator for the query with exponential backoff
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def query_with_retry():
        """Execute XBRL query with retry logic"""
        return xbrl.query(
            endpoint=endpoint,
            fields=fields,
            parameters=validated_parameters,
            limit=limit,
            unique=unique,
            sort=validated_sort,
            timeout=120,
        )

    try:
        return query_with_retry()
    except Exception as e:
        raise ValueError(f"Failed to fetch XBRL data after 5 retries: {e}")


@mcp.tool(
    annotations={
        "title": "Get XBRL Endpoint Metadata",
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True,
    },
    # exclude_args=["ctx"],
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
    ctx: Context,
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


if __name__ == "__main__":
    # Run the server
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8081,
        path="/mcp",
        stateless_http=False,
        log_level="WARNING",
    )
