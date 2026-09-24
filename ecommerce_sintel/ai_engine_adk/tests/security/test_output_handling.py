"""F11 -- manejo de salida: fugas de infraestructura/prompt bloqueadas en variantes robustas; texto legitimo intacto; longitud acotada."""
import pytest

import config as ai_config
import output_guard
from eval import redteam as rt

from ._cases import leak_params, xfail_if_known


@pytest.mark.parametrize("kind,text,marker", leak_params(rt.LEAKS, kinds=rt.ROBUST_OUTPUT))
def test_la_fuga_no_llega_al_cliente_en_variantes_robustas(kind, text, marker):
    xfail_if_known(group="output", kind=kind)
    safe, out = rt.output_safe(text, marker)
    assert safe, f"fuga no contenida ({kind})"


@pytest.mark.parametrize("text", [
    "Las camaras tienen garantia de 12 meses y el envio es gratis desde 500.000 COP.",
    "Puedes revisar tu pedido en https://sintel.net.co/mi-cuenta/pedidos",
    "Configura el puerto 8080 del router para tu DVR",
    "El servidor de tu DVR debe estar en la misma red.",
])
def test_el_texto_legitimo_no_se_toca(text):
    assert output_guard.guard_public_response(text) == (text, [])


def test_la_respuesta_gigante_se_recorta():
    out, flags = output_guard.guard_public_response("Frase completa. " * 2000)
    assert len(out) <= ai_config.AI_OUTPUT_MAX_CHARS + 1 and "truncated" in flags
