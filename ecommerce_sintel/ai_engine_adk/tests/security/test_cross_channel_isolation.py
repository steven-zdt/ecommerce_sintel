"""F11 -- aislamiento entre canales: el canal solo atribuye la memoria; una peticion no puede fijarlo a un valor arbitrario."""
import inspect

import main


def test_el_canal_desconocido_se_normaliza():
    src = inspect.getsource(main._chat_turn)
    assert 'req.channel if req.channel in ("web", "whatsapp") else "unknown"' in src


def test_el_canal_por_defecto_es_web_y_la_fuente_cliente():
    assert main.ChatRequest.model_fields["channel"].default == "web"
    assert main.ChatRequest.model_fields["source"].default == "customer"


def test_el_endpoint_exige_el_secreto_de_servicio_como_dependencia():
    route = next(r for r in main.app.routes if getattr(r, "path", "") == "/chat")
    deps = [getattr(d.dependency, "__name__", "") for d in route.dependencies]
    assert "require_service_token" in deps
