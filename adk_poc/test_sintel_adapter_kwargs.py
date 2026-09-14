"""
ADK-04 -- regresion del SINTEL Tool Adapter contra Tools REALES con `**kwargs`.

Hallazgo real (encontrado construyendo los 9 agentes de dominio reales de
ADK-04, no sintetico): 5 tools reales de `ai_engine/tools/core_tools.py`
(`CoreBannerUpdateTool`, `CoreBannerCreateTool`, `CoreNavbarLinkUpdateTool`,
`CoreNavbarLinkCreateTool`, `CoreBrandSliderUpdateTool` -- todas usadas por
`AdminAgent`) declaran su funcion real como `(ctx, campo_fijo, **kwargs)`.
El adapter original (ADK-02) solo sabia leer `inspect.signature(real_func)`
para construir la firma que el LLM ve -- eso rompe de 2 formas distintas con
`**kwargs`:

1. `ValueError: wrong parameter order` al construir el `inspect.Signature`
   del wrapper (un KEYWORD_ONLY despues de un VAR_KEYWORD es invalido) --
   crash duro, ni siquiera llegaba a construirse la FunctionTool.
2. Incluso arreglando el orden, un `**kwargs` puro no le muestra al LLM
   NINGUN campo opcional real (subtitle, link_url, link_label,
   display_order, etc.) -- el LLM jamas podria rellenarlos, aunque la tool
   real SI los acepta. Bug de correctness silencioso, no solo un crash.

Fix real (`sintel_adapter.py::adapt_sintel_tool`): cuando la funcion real
tiene un VAR_KEYWORD, se sintetizan parametros keyword-only adicionales
leyendo `ToolMetadata.args_schema.properties` -- la fuente REAL que YA
declara esos campos (ver `CORE_BANNER_CREATE_METADATA.args_schema` en
`core_tools.py`), no una inferencia inventada por el adapter.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool


class _FakeAdkToolContext:
    """Doble minimo de google.adk.tools.tool_context.ToolContext -- solo
    necesita `.state`, que es lo unico que `_sintel_ctx_from_adk_state` lee."""

    def __init__(self, state: dict):
        self.state = state


def _fake_tool_context(user_id=99, token="fake-jwt-admin"):
    return _FakeAdkToolContext(state={
        SINTEL_USER_STATE_KEY: {"id": user_id},
        SINTEL_TOKEN_STATE_KEY: token,
    })


def test_adapted_kwargs_tool_exposes_all_real_args_schema_fields_to_the_llm():
    """El wrapper.__signature__ (lo que ADK usa para declarar la tool al LLM)
    debe exponer los campos reales de args_schema, no solo los fijos --
    prueba directa del bug de correctness (2), sin necesitar Ollama."""
    import tools.core_tools as core_tools
    from tools.registry import get_tool

    registered = get_tool("CoreBannerCreateTool")
    assert registered is not None
    assert registered.func is core_tools.core_banner_create_tool

    adk_tool = adapt_sintel_tool(registered)
    import inspect
    param_names = set(inspect.signature(adk_tool.func).parameters)

    assert "title" in param_names, "El campo fijo 'title' no llego al wrapper"
    for optional_field in ("subtitle", "link_url", "link_label", "display_order"):
        assert optional_field in param_names, (
            f"'{optional_field}' viene de args_schema (**kwargs real) y no "
            f"aparecio en la firma del wrapper -- el LLM nunca lo veria"
        )
    assert "tool_context" in param_names


@pytest.mark.asyncio
async def test_adapted_kwargs_tool_forwards_provided_fields_and_drops_none():
    """Invocacion real (sin Ollama, sin mockear el adapter): el wrapper debe
    reenviar los campos que SI llegaron y descartar los None -- mismo
    criterio que la tool real ya aplica
    (`{k: v for k, v in kwargs.items() if v is not None}`, core_tools.py)."""
    from tools.registry import get_tool

    registered = get_tool("CoreBannerCreateTool")
    adk_tool = adapt_sintel_tool(registered)

    with patch(
        "tools.core_tools.django_internal_post", new=AsyncMock(return_value={"ok": True}),
    ) as mock_post:
        await adk_tool.func(
            title="Promo de fin de ano",
            subtitle="Hasta 30% en camaras",
            link_url=None,
            link_label=None,
            display_order=None,
            tool_context=_fake_tool_context(),
        )

    mock_post.assert_awaited_once()
    call_args = mock_post.call_args
    body = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("body")
    assert body == {"title": "Promo de fin de ano", "subtitle": "Hasta 30% en camaras"}, (
        f"El wrapper no filtro los campos None ni reenvio los reales correctamente: {body}"
    )
