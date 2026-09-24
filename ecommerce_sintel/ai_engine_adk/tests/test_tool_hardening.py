"""
HARDENING F4 (2026-09-24) -- Tools y agentes: clasificacion, validacion de argumentos, idempotencia, rate limit, auditoria.

Propuesta: ai_engine_adk/.AGENT/HARDENING_F4_PROPOSAL_2026-09-24.md. Sin red ni LLM: Redis simulado en memoria.
"""
import ast
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import config as ai_config
import idempotency
import sintel_adapter
from tools import registry as R
from tools.arg_validation import validate_args
from tools.classification import (
    FORCE_CONFIRMATION, RATE_LIMIT_DEFAULT_WRITE, RATE_LIMIT_HIGH_RISK, TOOL_LEVELS,
)

UUID = "3f2a9c1e-7b44-4d0a-9c11-5a1b2c3d4e5f"


#  C1: invariantes del registro 
def _metas():
    return [t.metadata for t in R._TOOLS.values()]


def test_hay_tools_registradas():
    assert len(_metas()) >= 50


def test_toda_tool_tiene_nivel_y_las_lecturas_son_nivel_0():
    for m in _metas():
        assert m.level >= 0, m.name
        if not m.side_effects:
            assert m.level == 0, f"lectura {m.name} no puede tener nivel > 0"


def test_toda_escritura_esta_clasificada_a_proposito():
    """Una escritura nueva NO puede colarse con el nivel por defecto: hay que clasificarla en TOOL_LEVELS."""
    for m in _metas():
        if m.side_effects:
            assert m.name in TOOL_LEVELS, f"escritura sin clasificar en TOOL_LEVELS: {m.name}"


def test_invariantes_de_escritura():
    for m in _metas():
        if not m.side_effects:
            continue
        assert m.rate_limit, f"{m.name} sin rate_limit"
        assert m.audit_level == "full", f"{m.name} sin auditoria completa"
        assert m.permissions, f"{m.name} sin permisos declarados"
        assert m.idempotent, f"{m.name} no idempotente"
        assert m.level in (1, 2, 3), f"{m.name} nivel invalido ({m.level}); el agente no tiene nivel 4"
        if m.level >= 2:
            assert m.requires_confirmation, f"{m.name} nivel {m.level} sin confirmacion"


def test_update_de_catalogo_y_servicios_piden_confirmacion():
    for name in FORCE_CONFIRMATION:
        assert R.get_tool(name).metadata.requires_confirmation, name


def test_borradores_de_creacion_siguen_sin_confirmacion():
    for name in ("CatalogBrandCreateDraftTool", "CatalogCategoryCreateDraftTool", "CatalogProductCreateDraftTool",
                 "ServiceCreateDraftTool"):
        assert not R.get_tool(name).metadata.requires_confirmation, name


def test_limites_por_riesgo_para_escrituras_sin_limite_propio():
    m = R.get_tool("CatalogTaxCreateTool").metadata  # risk=high, no declaraba limite
    assert m.rate_limit == RATE_LIMIT_HIGH_RISK
    b = R.get_tool("CatalogBrandCreateDraftTool").metadata  # risk=medium
    assert b.rate_limit == RATE_LIMIT_DEFAULT_WRITE
    assert R.get_tool("OpenSupportTicketTool").metadata.rate_limit == "10/hour/user"  # el declarado se respeta


def test_ninguna_tool_de_borrado_ni_nivel_4():
    assert not [m.name for m in _metas() if "delete" in m.name.lower() or "remove" in m.name.lower()]
    assert all(m.level != 4 for m in _metas())


def test_escaner_ast_sin_eval_exec_subprocess_en_tools():
    """Las Tools nunca ejecutan codigo/shell/SQL generado por el modelo."""
    builtins_bad = {"eval", "exec", "compile", "__import__"}  # solo el builtin (re.compile es legitimo)
    offenders = []
    tools_dir = Path(R.__file__).parent
    for py in tools_dir.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name) and f.id in builtins_bad:
                    offenders.append(f"{py.name}:{node.lineno}:{f.id}")
                if isinstance(f, ast.Attribute) and f.attr in ("eval", "exec", "system", "popen"):
                    offenders.append(f"{py.name}:{node.lineno}:{f.attr}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(m.split(".")[0] == "subprocess" for m in mods):
                    offenders.append(f"{py.name}:{node.lineno}:subprocess")
    assert not offenders, offenders


#  C2: validacion de argumentos 
SCHEMA = {
    "properties": {
        "uuid": {"type": "string"},
        "price": {"type": "number", "minimum": 1, "maximum": 1_000_000_000},
        "state": {"type": "string", "enum": ["draft", "published"]},
        "name": {"type": "string", "maxLength": 20},
        "tags": {"type": "array", "maxItems": 2},
        "active": {"type": "boolean"},
    },
    "required": ["uuid"],
}


def test_validate_ok():
    assert validate_args(SCHEMA, {"uuid": UUID, "price": 1500000, "state": "draft", "active": True}) == []


def test_validate_campo_desconocido_y_requerido():
    errs = validate_args(SCHEMA, {"admin": True, "price": 5})
    assert any("campo desconocido: admin" in e for e in errs) and any("falta el campo requerido: uuid" in e for e in errs)


def test_validate_uuid_malformado():
    assert any("UUID malformado" in e for e in validate_args(SCHEMA, {"uuid": "no-es-un-uuid"}))


def test_validate_precio_fuera_de_rango_y_no_numerico():
    assert any("mayor que el maximo" in e for e in validate_args(SCHEMA, {"uuid": UUID, "price": 10**12}))
    assert any("menor que el minimo" in e for e in validate_args(SCHEMA, {"uuid": UUID, "price": 0}))
    assert validate_args(SCHEMA, {"uuid": UUID, "price": "1500000"}) == []          # string numerico tolerado
    assert any("tipo invalido" in e for e in validate_args(SCHEMA, {"uuid": UUID, "price": {"amount": 5}}))  # dict NO
    assert any("tipo invalido" in e for e in validate_args(SCHEMA, {"uuid": UUID, "price": True}))
    assert any("no finito" in e for e in validate_args(SCHEMA, {"uuid": UUID, "price": float("inf")}))


def test_validate_enum_largo_y_lista():
    errs = validate_args(SCHEMA, {"uuid": UUID, "state": "hack", "name": "x" * 50, "tags": [1, 2, 3]})
    joined = " | ".join(errs)
    assert "valor fuera de los permitidos" in joined and "texto demasiado largo" in joined and "demasiados elementos" in joined


def test_validate_errores_no_incluyen_valores():
    errs = validate_args(SCHEMA, {"uuid": "SECRETO-123", "state": "TOKEN-XYZ"})
    assert "SECRETO-123" not in " ".join(errs) and "TOKEN-XYZ" not in " ".join(errs)


def _tool(name):
    return SimpleNamespace(name=name)


def test_callback_monitor_deja_pasar_pero_loguea(monkeypatch, caplog):
    monkeypatch.setattr(ai_config, "AI_TOOL_STRICT_ARGS", False)
    with caplog.at_level(logging.WARNING, logger="sintel_adapter"):
        out = sintel_adapter.validate_tool_args_before(tool=_tool("CatalogProductGetTool"), args={"uuid": "malo", "x": 1},
                                                       tool_context=None)
    assert out is None
    assert "ai_tool_args_invalid mode=monitor" in caplog.text and "malo" not in caplog.text


def test_callback_estricto_rechaza_con_400(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_TOOL_STRICT_ARGS", True)
    out = sintel_adapter.validate_tool_args_before(tool=_tool("CatalogProductGetTool"), args={"uuid": "malo"}, tool_context=None)
    assert out["status_code"] == 400 and out["validation_errors"]


def test_callback_args_validos_no_bloquean(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_TOOL_STRICT_ARGS", True)
    assert sintel_adapter.validate_tool_args_before(tool=_tool("CatalogProductGetTool"), args={"uuid": UUID}, tool_context=None) is None


def test_callback_tool_desconocida_no_falla():
    assert sintel_adapter.validate_tool_args_before(tool=_tool("NoExiste"), args={"a": 1}, tool_context=None) is None


def test_callback_encadenado_en_los_agentes():
    """El agente usa AMBOS callbacks: tope por turno y validacion de argumentos."""
    import sintel_root_workflow as wf

    agent = wf.get_domain_agent("SupportAgent")
    cbs = agent.before_tool_callback
    assert sintel_adapter.deny_after_max_tool_calls_per_turn in cbs and sintel_adapter.validate_tool_args_before in cbs


#  C3: idempotencia (Redis simulado) 
class FakeRedis:
    store: dict = {}

    def __init__(self, *_a, **_k):
        pass

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)

    async def aclose(self):
        pass


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    FakeRedis.store = {}
    monkeypatch.setattr(idempotency, "_client", lambda: FakeRedis())
    monkeypatch.setattr(ai_config, "AI_TOOL_IDEMPOTENCY_ENABLED", True)

    async def _no_limit(*a, **k):
        return False

    monkeypatch.setattr(sintel_adapter, "rate_limit_exceeded", _no_limit)


def test_make_key_estable_y_sensible_a_los_args():
    a = idempotency.make_key("s1", 7, "T", {"a": 1, "b": 2})
    assert a == idempotency.make_key("s1", 7, "T", {"b": 2, "a": 1})
    assert a != idempotency.make_key("s1", 7, "T", {"a": 1, "b": 3})
    assert a != idempotency.make_key("s2", 7, "T", {"a": 1, "b": 2})   # otra sesion
    assert a != idempotency.make_key("s1", 8, "T", {"a": 1, "b": 2})   # otro usuario


async def test_begin_finish_replay_y_abort():
    key = "ai:idem:k1"
    assert await idempotency.begin(key) == (None, True)
    assert await idempotency.begin(key) == (idempotency.PENDING, False)    # en curso
    await idempotency.finish(key, {"uuid": "x", "ok": True})
    assert await idempotency.begin(key) == ({"uuid": "x", "ok": True}, False)  # replay
    await idempotency.abort(key)
    assert await idempotency.begin(key) == (None, True)


def _build_write_tool(monkeypatch, calls, result=None, name="CatalogBrandCreateDraftTool"):
    reg = R.get_tool(name)

    async def fake_func(ctx, **kw):
        calls.append(kw)
        return result if result is not None else {"uuid": "nuevo", "name": kw.get("name")}

    monkeypatch.setattr(reg, "func", fake_func)
    tool = sintel_adapter.adapt_sintel_tool(reg)
    fn = tool.func
    ctx = SimpleNamespace(
        state={sintel_adapter.SINTEL_USER_STATE_KEY: {"user_id": 9, "is_staff": True, "is_superuser": True}},
        session=SimpleNamespace(id="sess-1"), invocation_id="inv-1", agent_name="CatalogAgent",
    )
    monkeypatch.setattr(sintel_adapter, "_sintel_ctx_from_adk_state",
                        lambda tc: SimpleNamespace(user={"user_id": 9, "is_staff": True, "is_superuser": True}, token="t"))
    monkeypatch.setattr(sintel_adapter, "user_lacks_admin_permission", lambda *a, **k: False)
    return fn, ctx


async def test_escritura_identica_no_se_ejecuta_dos_veces(monkeypatch):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls)
    first = await fn(name="Marca X", tool_context=ctx)
    second = await fn(name="Marca X", tool_context=ctx)
    assert len(calls) == 1
    assert first == {"uuid": "nuevo", "name": "Marca X"}
    assert second["idempotent_replay"] is True and second["uuid"] == "nuevo"


async def test_args_distintos_si_ejecutan(monkeypatch):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls)
    await fn(name="A", tool_context=ctx)
    await fn(name="B", tool_context=ctx)
    assert len(calls) == 2


async def test_un_fallo_no_bloquea_el_reintento(monkeypatch):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls, result={"error": "boom", "status_code": 500})
    await fn(name="A", tool_context=ctx)
    await fn(name="A", tool_context=ctx)
    assert len(calls) == 2  # el resultado con error no se cachea


async def test_operacion_identica_en_curso_devuelve_409(monkeypatch):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls)
    key = idempotency.make_key("sess-1", 9, "CatalogBrandCreateDraftTool", {"name": "A"})
    FakeRedis.store[key] = idempotency.PENDING
    out = await fn(name="A", tool_context=ctx)
    assert out["status_code"] == 409 and calls == []


async def test_rate_limit_libera_la_clave_de_idempotencia(monkeypatch):
    calls = []

    async def limited(*a, **k):
        return True

    fn, ctx = _build_write_tool(monkeypatch, calls)
    monkeypatch.setattr(sintel_adapter, "rate_limit_exceeded", limited)
    out = await fn(name="A", tool_context=ctx)
    assert out["status_code"] == 429 and calls == [] and FakeRedis.store == {}


async def test_idempotencia_apagada_ejecuta_siempre(monkeypatch):
    calls = []
    monkeypatch.setattr(ai_config, "AI_TOOL_IDEMPOTENCY_ENABLED", False)
    fn, ctx = _build_write_tool(monkeypatch, calls)
    await fn(name="A", tool_context=ctx)
    await fn(name="A", tool_context=ctx)
    assert len(calls) == 2


async def test_lecturas_no_pasan_por_idempotencia(monkeypatch):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls, name="CatalogProductGetTool", result={"uuid": UUID})
    await fn(uuid=UUID, tool_context=ctx)
    await fn(uuid=UUID, tool_context=ctx)
    assert len(calls) == 2 and FakeRedis.store == {}


#  C5: auditoria estructurada 
async def test_auditoria_un_evento_por_ejecucion_sin_argumentos(monkeypatch, caplog):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls)
    with caplog.at_level(logging.INFO, logger="sintel_adapter"):
        await fn(name="DatoSensible-999", tool_context=ctx)
    events = [r.getMessage() for r in caplog.records if r.getMessage().startswith("ai_tool_audit")]
    assert len(events) == 1
    ev = events[0]
    for field in ("invocation_id=inv-1", "session_id=sess-1", "user_id=9", "agent=CatalogAgent",
                  "tool=CatalogBrandCreateDraftTool", "level=1", "authz=allowed", "status=ok", "latency_ms="):
        assert field in ev, field
    assert "DatoSensible-999" not in ev  # nunca argumentos ni valores


async def test_auditoria_de_denegacion(monkeypatch, caplog):
    calls = []
    fn, ctx = _build_write_tool(monkeypatch, calls)
    monkeypatch.setattr(sintel_adapter, "user_lacks_admin_permission", lambda *a, **k: True)
    with caplog.at_level(logging.INFO, logger="sintel_adapter"):
        out = await fn(name="A", tool_context=ctx)
    assert out["status_code"] == 403 and calls == []
    assert any("authz=denied" in r.getMessage() for r in caplog.records)
