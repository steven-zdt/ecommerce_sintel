"""
FASE 10 integracion Meta Business: MetaAdsMCPClient.

No requiere el paquete `mcp` instalado ni red: se mockea `_open_session` (que es
donde viven los imports perezosos del SDK) para entregar una sesion falsa.
"""
import asyncio
from contextlib import asynccontextmanager

import pytest

from mcp_client.client import MetaAdsMCPClient


# --- dobles de la sesion MCP ----------------------------------------------

class _Tool:
    def __init__(self, name, description="", schema=None):
        self.name = name
        self.description = description
        self.inputSchema = schema or {}


class _ListResult:
    def __init__(self, tools):
        self.tools = tools


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _CallResult:
    def __init__(self, content, is_error=False, structured=None):
        self.content = content
        self.isError = is_error
        self.structuredContent = structured


class _FakeSession:
    def __init__(self, *, tools=None, call_result=None, call_exc=None):
        self._tools = tools or []
        self._call_result = call_result
        self._call_exc = call_exc
        self.call_tool_calls = []

    async def list_tools(self):
        return _ListResult(self._tools)

    async def call_tool(self, name, arguments):
        self.call_tool_calls.append((name, arguments))
        if self._call_exc is not None:
            raise self._call_exc
        return self._call_result


def _patch_session(monkeypatch, client, session):
    @asynccontextmanager
    async def _cm(**_kw):
        yield session
    monkeypatch.setattr(client, "_open_session", lambda **kw: _cm(**kw))


def _make_client(monkeypatch, *, authorized=True, allow_writes=False):
    client = MetaAdsMCPClient(allow_writes=allow_writes)
    monkeypatch.setattr(client, "is_authorized", lambda: authorized)
    return client


# --- tests ---------------------------------------------------------------

async def test_list_tools_unauthorized_does_not_connect(monkeypatch):
    client = _make_client(monkeypatch, authorized=False)
    called = {"open": False}
    monkeypatch.setattr(client, "_open_session", lambda **kw: called.__setitem__("open", True))
    out = await client.list_tools()
    assert out["authorized"] is False
    assert "authorize" in out["error"].lower()
    assert called["open"] is False


async def test_list_tools_ok_tags_each_tool_with_policy(monkeypatch):
    client = _make_client(monkeypatch)
    session = _FakeSession(tools=[_Tool("get_campaigns"), _Tool("create_campaign")])
    _patch_session(monkeypatch, client, session)
    out = await client.list_tools()
    assert out == {
        "authorized": True,
        "count": 2,
        "tools": [
            {"name": "get_campaigns", "description": "", "input_schema": {}, "policy": "allow"},
            {"name": "create_campaign", "description": "", "input_schema": {}, "policy": "deny"},
        ],
    }


async def test_call_tool_blocks_write_without_opening_session(monkeypatch):
    client = _make_client(monkeypatch, allow_writes=False)
    session = _FakeSession(call_result=_CallResult([_TextBlock("nope")]))
    _patch_session(monkeypatch, client, session)
    out = await client.call_tool("pause_campaign", {"id": "c1"})
    assert out["policy"] == "deny"
    assert session.call_tool_calls == []  # nunca se llamo


async def test_call_tool_read_ok_serializes_content(monkeypatch):
    client = _make_client(monkeypatch)
    session = _FakeSession(call_result=_CallResult(
        [_TextBlock("hola")], structured={"campaigns": [{"id": "c1"}]},
    ))
    _patch_session(monkeypatch, client, session)
    out = await client.call_tool("get_campaigns", {"limit": 5})
    assert out["is_error"] is False
    assert out["content"] == [{"type": "text", "text": "hola"}]
    assert out["structured"] == {"campaigns": [{"id": "c1"}]}
    assert session.call_tool_calls == [("get_campaigns", {"limit": 5})]


async def test_call_tool_wraps_timeout_as_transient(monkeypatch):
    client = _make_client(monkeypatch)
    session = _FakeSession(call_exc=asyncio.TimeoutError())
    _patch_session(monkeypatch, client, session)
    out = await client.call_tool("get_campaigns")
    assert out.get("transient") is True


async def test_call_tool_wraps_auth_error(monkeypatch):
    client = _make_client(monkeypatch)
    session = _FakeSession(call_exc=RuntimeError("HTTP 401 Unauthorized"))
    _patch_session(monkeypatch, client, session)
    out = await client.call_tool("get_campaigns")
    assert out.get("authorized") is False


async def test_ping_ok(monkeypatch):
    client = _make_client(monkeypatch)
    _patch_session(monkeypatch, client, _FakeSession(tools=[_Tool("get_campaigns")]))
    out = await client.ping()
    assert out["ok"] is True
    assert out["tool_count"] == 1


async def test_ping_unauthorized(monkeypatch):
    client = _make_client(monkeypatch, authorized=False)
    out = await client.ping()
    assert out["ok"] is False
    assert out["authorized"] is False


def _server_without_client_id(client):
    from dataclasses import replace
    return replace(client._srv, client_id="")


def test_build_oauth_provider_without_client_id_raises(monkeypatch):
    from mcp_client.client import MCPClientError
    client = MetaAdsMCPClient()
    client._srv = _server_without_client_id(client)
    with pytest.raises(MCPClientError) as ei:
        client.build_oauth_provider()
    msg = str(ei.value)
    assert "client_id" in msg.lower() or "META_APP_ID" in msg


async def test_list_tools_surfaces_missing_client_id(monkeypatch):
    client = MetaAdsMCPClient()
    client._srv = _server_without_client_id(client)
    monkeypatch.setattr(client, "is_authorized", lambda: True)
    out = await client.list_tools()
    assert out["authorized"] is False
    assert "client_id" in out["error"].lower() or "META_APP_ID" in out["error"]
