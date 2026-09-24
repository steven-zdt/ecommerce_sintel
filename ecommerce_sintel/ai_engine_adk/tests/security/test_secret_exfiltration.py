"""F11 -- exfiltracion de secretos: JWT/Bearer/claves/contrasenas se redactan aunque el modelo los escriba en una variante."""
import pytest

from eval import redteam as rt

from ._cases import attack_params, leak_params


@pytest.mark.parametrize("kind,text,marker", leak_params(rt.SECRETS, kinds=rt.ROBUST_OUTPUT_SECRETS))
def test_el_secreto_no_sale_en_claro(kind, text, marker):
    safe, out = rt.output_safe(text, marker)
    assert safe, f"el secreto sale en la variante {kind}"


def test_el_valor_exacto_de_un_secreto_del_entorno_se_redacta(monkeypatch):
    import output_guard

    secret = "s3cr3t-service-token-de-prueba-0123456789"
    monkeypatch.setenv("AI_SERVICE_TOKEN", secret)
    out, flags = output_guard.guard_public_response(f"valor: {secret}")
    assert secret not in out and flags


@pytest.mark.parametrize("category,kind,text", attack_params(categories={"secret_request"}, kinds={"plain"}))
def test_la_peticion_de_secretos_se_detecta_en_su_forma_llana(category, kind, text):
    assert "secret_request" in rt.detected_categories(text)
