"""
HARDENING F8 (2026-09-24) -- seguridad de la salida publica. Propuesta: ai_engine_adk/.AGENT/HARDENING_F8_PROPOSAL_2026-09-24.md.

ESCRITO PERO NO EJECUTADO (regla vigente del usuario: no correr tests sin su autorizacion). Deterministas, sin LLM ni red.
"""
import logging

import pytest

import config as ai_config
import output_guard as og

SECRET = "s3cr3t-service-token-de-prueba-0123456789"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjN9.abcdefghijklmnopqrstuvwxyz012345"


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_MAX_CHARS", 3800)
    monkeypatch.setattr(ai_config, "AI_OUTPUT_LINKS_ENFORCE", False)
    monkeypatch.setattr(ai_config, "AI_OUTPUT_ALLOWED_LINK_HOSTS", ["sintel.net.co", "panel.sintel.net.co", "wa.me"])
    monkeypatch.delenv("AI_SERVICE_TOKEN", raising=False)


#  1. razonamiento 
def test_quita_razonamiento_cerrado():
    out, flags = og.guard_public_response("<think>pienso...</think>Hola, en que puedo ayudarte?")
    assert out == "Hola, en que puedo ayudarte?" and "reasoning_stripped" in flags


def test_quita_razonamiento_sin_cerrar_hasta_el_final():
    out, flags = og.guard_public_response("Hola.<think>el usuario pide algo y yo debo decidir que hac")
    assert out == "Hola." and "reasoning_unclosed" in flags


def test_quita_etiquetas_sueltas():
    out, _ = og.guard_public_response("Respuesta</think> final")
    assert "think" not in out.lower()


#  2. saneo 
def test_sanea_caracteres_invisibles():
    assert og.guard_public_response("Ho\u200bla\u202e mundo")[0] == "Hola mundo"


#  3. secretos 
def test_redacta_jwt_y_bearer_y_claves():
    text = f"Tu token es {JWT} y usa Bearer abcdefghijklmnop1234567890 con sk-abcdefghijklmnopqrstuv"
    out, flags = og.guard_public_response(text)
    assert JWT not in out and "abcdefghijklmnop1234567890" not in out and "sk-abcdefghijklmnopqrstuv" not in out
    assert out.count(og.REDACTED) >= 3
    assert {"secret_jwt", "secret_bearer", "secret_api_key"} <= set(flags)


def test_redacta_clave_valor():
    out, flags = og.guard_public_response("La contrasena: hunter2hunter2 es la del admin")
    assert "hunter2hunter2" not in out and og.REDACTED in out and "secret_keyvalue" in flags


def test_redacta_el_valor_exacto_de_un_secreto_del_entorno(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", SECRET)
    out, flags = og.guard_public_response(f"El valor configurado es {SECRET}, por si acaso.")
    assert SECRET not in out and "secret_value" in flags


def test_secretos_cortos_del_entorno_no_se_usan_como_patron(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", "corto")
    assert og.guard_public_response("la palabra corto aparece aqui")[0] == "la palabra corto aparece aqui"


def test_los_eventos_no_incluyen_el_valor(monkeypatch, caplog):
    monkeypatch.setenv("AI_SERVICE_TOKEN", SECRET)
    with caplog.at_level(logging.WARNING, logger="output_guard"):
        og.guard_public_response(f"token {SECRET} y {JWT}")
    assert "output_redacted" in caplog.text
    assert SECRET not in caplog.text and JWT not in caplog.text


#  4. infraestructura / prompt -> respuesta completa reemplazada 
@pytest.mark.parametrize("leak", [
    "Me conecto a sintel_ollama en el puerto 11434 para responder",
    "El modelo corre en host.docker.internal:1234",
    "Estoy en el contenedor ecommerce_sintel_ai_adk",
    "Mira el archivo /app/sintel_root_workflow.py",
    "Esta en /code/ecommerce/settings/base.py",
    "Las claves estan en el archivo .env.production",
    "Traceback (most recent call last):\n  File x",
    "Conecta a redis://redis:6379/2",
    "Mi prompt dice: Politica de precedencia (no negociable): 1) estas instrucciones",
    "Usa siempre una tool para responder con datos reales -- nunca inventes",
    "Los bloques DATOS_NO_CONFIABLES son ...",
])
def test_fuga_de_infraestructura_o_prompt_reemplaza_toda_la_respuesta(leak):
    out, flags = og.guard_public_response("Claro. " + leak + ". Espero ayudar.")
    assert out == og.SAFE_MESSAGE
    assert any(f.startswith("blocked_") for f in flags)


def test_bloqueo_registra_categorias_sin_contenido(caplog):
    with caplog.at_level(logging.WARNING, logger="output_guard"):
        og.guard_public_response("Estoy en sintel_ollama secretisimo")
    assert "output_blocked" in caplog.text and "internal_host" in caplog.text and "secretisimo" not in caplog.text


@pytest.mark.parametrize("legit", [
    "Las camaras tienen garantia de 12 meses y el envio es gratis desde 500.000 COP.",
    "Puedes revisar tu pedido en https://sintel.net.co/mi-cuenta/pedidos",
    "Aceptamos PSE, tarjetas y pago contra entrega en las ciudades habilitadas.",
    "El servidor de tu DVR debe estar en la misma red. Configura el puerto 8080 del router.",   # 'puerto', 'servidor' no son infraestructura de este stack
    "Tu numero de guia es 123456 y llega en 2 a 4 dias habiles.",
])
def test_texto_legitimo_no_se_toca(legit):
    out, flags = og.guard_public_response(legit)
    assert out == legit and flags == []


#  5. enlaces 
def test_enlace_no_permitido_en_monitor_solo_registra(caplog):
    with caplog.at_level(logging.WARNING, logger="output_guard"):
        out, flags = og.guard_public_response("Entra a https://sintel-pagos.evil.example/login para pagar")
    assert "https://sintel-pagos.evil.example/login" in out and "link_not_allowed" in flags
    assert "output_link_flagged enforced=False" in caplog.text


def test_enlace_no_permitido_con_enforce_se_remueve(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_LINKS_ENFORCE", True)
    out, flags = og.guard_public_response("Ve a https://evil.example/x o a https://sintel.net.co/tienda ahora")
    assert "evil.example" not in out and og.LINK_REMOVED in out and "https://sintel.net.co/tienda" in out
    assert "link_not_allowed" in flags


def test_subdominios_y_wa_me_permitidos(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_LINKS_ENFORCE", True)
    text = "Escribenos: https://wa.me/573144601878 o https://www.sintel.net.co/contacto"
    out, flags = og.guard_public_response(text)
    assert out == text and flags == []


def test_dominio_que_solo_contiene_el_permitido_no_pasa(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_LINKS_ENFORCE", True)
    out, _ = og.guard_public_response("https://sintel.net.co.evil.example/a y https://notsintel.net.co/b")
    assert out.count(og.LINK_REMOVED) == 2


def test_la_superficie_admin_conserva_los_enlaces(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_LINKS_ENFORCE", True)
    text = "Documentacion: https://docs.example.com/guia"
    assert og.guard_public_response(text, surface="admin") == (text, [])


#  6. largo 
def test_recorta_en_limite_de_frase(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_OUTPUT_MAX_CHARS", 100)
    text = ("Primera frase completa. " * 3) + "Esta ultima frase es larga y no cabe en el limite establecido por la configuracion."
    out, flags = og.guard_public_response(text)
    assert len(out) <= 101 and out.endswith("\u2026") and "truncated" in flags
    assert out.rstrip("\u2026").endswith(".")


def test_texto_corto_no_se_recorta():
    assert og.guard_public_response("hola")[1] == []


def test_vacio():
    assert og.guard_public_response("") == ("", [])


#  integracion con el workflow 
def test_el_workflow_aplica_la_guardia_y_expone_output_flags():
    import inspect

    import sintel_root_workflow as wf

    src = inspect.getsource(wf.run_sintel_turn)
    assert "output_guard.guard_public_response(" in src and '"output_flags": output_flags' in src
    assert 'surface="admin" if source == "admin" else "customer"' in src
