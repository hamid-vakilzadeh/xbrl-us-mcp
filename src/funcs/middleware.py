"""Session-based authentication middleware for XBRL-US MCP server."""

import hashlib
from xbrl_us import XBRL
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import BaseModel, Field
import logging
from typing import Optional
import time

# Simple session-scoped storage using FastMCP session IDs
_session_data = {}

logger = logging.getLogger(__name__)


class ConfigSchema(BaseModel):
    username: str = Field(description="xbrl.us username username")
    password: str = Field(description="xbrl.us password")
    client_id: str = Field(description="xbrl.us client ID")
    client_secret: str = Field(description="xbrl.us client secret")


class SessionAuthMiddleware(Middleware):
    """
    Middleware that handles authentication for xbrl-us MCP.

    This middleware:
    1. Checks if a valid session exists for the current request
    2. If not, authenticates using user credentials
    3. Stores credentials in context state for tools to access
    """

    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Handle session-based XBRL authentication for MCP requests.

        This middleware:
        1. Extracts session ID from the request
        2. Checks if a valid XBRL instance exists for the session
        3. Creates a new XBRL instance if needed or if token is expired
        4. Stores the XBRL instance in context state for tools to access

        Args:
            context: The middleware context containing request information
            call_next: Function to continue the middleware chain
        """
        try:
            # Extract session ID and credentials
            session_id = self._get_session_id(context)
            config = await self._extract_credentials_from_request()

            if not config:
                logger.warning("No credentials provided in request")
                # Store None in context to indicate no authentication
                if context.fastmcp_context:
                    context.fastmcp_context.set_state("xbrl", None)
                return await call_next(context)

            # Validate config schema
            config = ConfigSchema.model_validate(config)
            credentials_hash = self._hash_credentials(config)

            # Check if we have a valid session
            session_data = _session_data.get(session_id)
            xbrl_instance = None

            if session_data:
                stored_xbrl = session_data.get("xbrl_instance")
                stored_hash = session_data.get("credentials_hash")

                # Check if credentials match and XBRL instance is still valid
                if (
                    stored_hash == credentials_hash
                    and stored_xbrl
                    and self._is_xbrl_valid(stored_xbrl)
                ):
                    xbrl_instance = stored_xbrl
                    logger.info(f"Reusing valid XBRL session for {session_id}")

                else:
                    logger.info(
                        f"Session {session_id} invalid or expired, creating new one"
                    )

            # Create new XBRL instance if needed
            if not xbrl_instance:
                xbrl_instance = await self._authenticate_user(config)
                _session_data[session_id] = {
                    "xbrl_instance": xbrl_instance,
                    "credentials_hash": credentials_hash,
                    "created_at": time.time(),
                }
                logger.info(
                    f"New XBRL instance created for session {session_id}: {xbrl_instance.access_token[:5]}..."
                )

            # Store XBRL instance in context state for tools to access
            if context.fastmcp_context:
                context.fastmcp_context.set_state("xbrl", xbrl_instance)
                logger.info(
                    f"XBRL instance stored in context: {xbrl_instance.access_token[:5]}..."
                )

            # Continue with the request
            return await call_next(context)

        except Exception as e:
            logger.error(f"Session authentication failed: {e}")
            # Store None in context to indicate authentication failure
            if context.fastmcp_context:
                context.fastmcp_context.set_state("xbrl", None)
            # Don't fail the request - let tools handle the error
            return await call_next(context)

    async def _extract_credentials_from_request(self) -> Optional[str]:
        """
        Extract XBRL Credentials from HTTP request.

        Args:
            context: The middleware context

        Returns:
            API key if found, None otherwise
        """
        try:
            from fastmcp.server.dependencies import get_http_request

            request = get_http_request()
            if not request:
                return None

            # Try to extract from URL if available
            if hasattr(request, "url"):
                import urllib.parse

                parsed = urllib.parse.urlparse(str(request.url))
                params = urllib.parse.parse_qs(parsed.query)
                if params:
                    try:
                        auth_config = dict(
                            username=params.get("username", [None])[0],
                            password=params.get("password", [None])[0],
                            client_id=params.get("client_id", [None])[0],
                            client_secret=params.get("client_secret", [None])[0],
                        )
                        return auth_config

                    except Exception as e:
                        logger.error(f"Failed to parse config: {e}")
            else:
                logger.warning("no credentials found")
                return None

        except Exception as e:
            logger.debug(f"Could not extract API key from request: {e}")
            return None

    def _get_session_id(self, context: MiddlewareContext) -> str:
        """
        Extract the proper session ID from FastMCP context.

        Args:
            context: The middleware context

        Returns:
            Session ID string from FastMCP context or fallback
        """
        try:
            # Use FastMCP's built-in session ID from context
            if context.fastmcp_context:
                session_id = context.fastmcp_context.session_id
                logger.debug(f"Using FastMCP session ID: {session_id}")
                return session_id

        except Exception as e:
            logger.debug(f"Could not extract FastMCP session ID: {e}")

    def _hash_credentials(self, config: ConfigSchema) -> str:
        """
        Create a hash of the credentials for comparison.

        Args:
            config: The configuration containing credentials

        Returns:
            SHA256 hash of the credentials
        """
        credential_string = f"{config.username}:{config.password}:{config.client_id}:{config.client_secret}"
        return hashlib.sha256(credential_string.encode()).hexdigest()

    def _is_xbrl_valid(self, xbrl_instance: XBRL) -> bool:
        """Check if XBRL instance has a valid, non-expired token."""
        try:
            return (
                hasattr(xbrl_instance, "_access_token_expires_at")
                and xbrl_instance._access_token_expires_at > time.time()
            )
        except Exception as e:
            logger.warning(f"Error checking XBRL token validity: {e}")
            return False

    async def _authenticate_user(self, config: ConfigSchema) -> XBRL:
        """
        Authenticate user using provided XBRL credentials.

        Args:
            config: The validated configuration containing credentials

        Returns:
            Authenticated XBRL instance
        """
        try:
            xbrl_us = XBRL(
                username=config.username,
                password=config.password,
                client_id=config.client_id,
                client_secret=config.client_secret,
            )

            return xbrl_us

        except Exception as e:
            raise ValueError(
                f"XBRL credentials are invalid. Please enter valid credentials. {e}"
            )
