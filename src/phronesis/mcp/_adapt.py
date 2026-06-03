"""Bidirectional adapters between phronesis :class:`Tool` and MCP tools.

Two adaptation paths are needed:

* **Client side** - a remote MCP tool definition is wrapped in a
  phronesis :class:`Tool` so it can be plugged into an
  :class:`~phronesis.agents.Agent`. The remote inputSchema is preserved
  verbatim; argument validation is delegated to the remote server.
* **Server side** - a local phronesis :class:`Tool` is exported as an
  :class:`mcp.types.Tool` so a :class:`PhronesisMcpServer` can publish
  it over any MCP transport.

The client adapter is the more interesting one: it builds a
:class:`Tool` instance directly (bypassing the :func:`tool` decorator)
because there is no Python function to derive a schema from. The
adapter:

1. Defines a thin ``async def _remote_call(**kwargs)`` stub whose
   sole role is to satisfy :class:`Tool`'s constructor; the validator
   built from its ``**kwargs`` signature accepts any argument dict.
2. Overrides :meth:`Tool.schema` with the remote ``inputSchema`` so
   the LLM sees the contract the server actually publishes.
3. Performs the real call by invoking the :class:`mcp.ClientSession`
   inside the stub.

Errors raised by the remote server are translated to
:class:`ToolError` subclasses so a failure on the MCP side does not
abort the surrounding agent run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import mcp.types as mcp_types

from phronesis.mcp.errors import McpToolNotFoundError
from phronesis.tools.errors import ToolError, ToolNotFoundError, ToolTimeoutError
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from phronesis.mcp.client import McpClient


def _content_blocks_to_payload(
    blocks: list[
        mcp_types.TextContent
        | mcp_types.ImageContent
        | mcp_types.AudioContent
        | mcp_types.ResourceLink
        | mcp_types.EmbeddedResource
    ],
) -> Any:
    """Collapse an MCP content list to a phronesis-friendly payload.

    * Empty list -> ``None``.
    * Single text block -> its raw string.
    * Anything else -> a list of dicts produced by ``model_dump``.
    """
    if not blocks:
        return None

    if len(blocks) == 1 and isinstance(blocks[0], mcp_types.TextContent):
        return blocks[0].text

    return [block.model_dump(by_alias=True, exclude_none=True) for block in blocks]


def _call_tool_result_to_payload(result: mcp_types.CallToolResult) -> Any:
    """Translate a successful :class:`mcp.types.CallToolResult` to a Python value.

    ``structuredContent`` wins over the textual content list when
    present.
    """
    if result.structuredContent is not None:
        return result.structuredContent

    return _content_blocks_to_payload(list(result.content))


def _error_from_result(
    tool_name: str,
    result: mcp_types.CallToolResult,
) -> ToolError:
    """Build a :class:`ToolError` from an ``isError=True`` MCP result."""
    payload = _content_blocks_to_payload(list(result.content))
    message = payload if isinstance(payload, str) else f"MCP tool {tool_name!r} returned an error."

    return ToolError(message, details={"tool": tool_name, "payload": payload})


def mcp_tool_to_phronesis_tool(
    client: McpClient,
    mcp_tool: mcp_types.Tool,
    *,
    server_name: str,
) -> Tool:
    """Wrap a remote MCP tool definition as a phronesis :class:`Tool`.

    The returned tool can be injected into an agent via
    :meth:`Agent.with_added_tools`. Its canonical id is
    ``phronesis.mcp.<server_name>.<mcp_tool.name>``.

    Args:
        client: Live :class:`McpClient` owning the session that the
            adapted tool will call into.
        mcp_tool: The MCP tool definition returned by the server.
        server_name: Server name as declared in the
            :class:`McpServerSpec`; used to derive a stable
            :class:`ToolId`.

    Returns:
        A :class:`Tool` whose schema mirrors the remote ``inputSchema``
        and whose invocation forwards every argument to the remote
        server.
    """
    remote_name = mcp_tool.name
    description = mcp_tool.description or ""
    input_schema = dict(mcp_tool.inputSchema or {})

    canonical = f"phronesis.mcp.{server_name}.{remote_name}".lower()
    spec = ToolSpec(
        id=ToolId(canonical),
        name=ToolName(remote_name),
        description=description,
        input_schema=input_schema,
    )

    async def _remote_call(**kwargs: Any) -> Any:
        return await _invoke_remote(client, remote_name, kwargs)

    _remote_call.__name__ = remote_name
    _remote_call.__qualname__ = remote_name
    _remote_call.__doc__ = description or None

    tool = Tool(_remote_call, spec, lazy=True)
    tool.schema(lambda: dict(input_schema))
    # The remote server validates arguments against its own schema; the
    # local validator built from ``**kwargs`` would otherwise drop them.
    tool._validator = lambda values: dict(values)

    return tool


async def _invoke_remote(
    client: McpClient,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """Forward an invocation to the remote server and translate the result."""
    session = client.session

    try:
        result = await session.call_tool(name=tool_name, arguments=arguments)
    except TimeoutError as exc:
        raise ToolTimeoutError(
            f"MCP tool {tool_name!r} timed out.",
            details={"tool": tool_name},
        ) from exc
    except McpToolNotFoundError as exc:
        raise ToolNotFoundError(str(exc), details={"tool": tool_name}) from exc
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(
            f"MCP tool {tool_name!r} failed: {exc}",
            details={"tool": tool_name},
        ) from exc

    if result.isError:
        raise _error_from_result(tool_name, result)

    return _call_tool_result_to_payload(result)


def phronesis_tool_to_mcp_definition(tool: Tool) -> mcp_types.Tool:
    """Project a phronesis :class:`Tool` into an :class:`mcp.types.Tool`.

    The MCP ``name``/``description``/``inputSchema`` are taken from
    the tool's :attr:`Tool.spec` and the canonical JSON schema
    produced by :meth:`Tool.get_schema`.
    """
    return mcp_types.Tool(
        name=str(tool.spec.name),
        description=tool.spec.description or None,
        inputSchema=tool.get_schema(),
    )


def payload_to_content_blocks(payload: Any) -> list[mcp_types.TextContent]:
    """Wrap a tool return value in the minimal MCP content list.

    Anything non-string is JSON-encoded so the server-side handler
    can always return a single :class:`mcp.types.TextContent`. This
    keeps v1 simple; richer content types are deferred to v2.
    """
    import json

    if isinstance(payload, str):
        text = payload
    elif payload is None:
        text = ""
    else:
        try:
            text = json.dumps(payload, default=str)
        except (TypeError, ValueError):
            text = str(payload)

    return [mcp_types.TextContent(type="text", text=text)]
