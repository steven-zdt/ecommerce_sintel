"""
Mision RAG Enterprise (2026-09-16, FASE 2 -- metadata filtering).
`detect_apps_from_text()` (retrievers.py) es el paso real de "derive
retrieval constraints" del diagrama de la mision (query -> filtro de
metadata ANTES de la busqueda vectorial/exacta) -- ya existia desde la era
ChromaDB, cubierto indirectamente por
test_retrieve_knowledge_for_chat.py::test_retrieve_knowledge_for_chat_envia_query_y_apps_detectados.
Este archivo lo prueba directo (funcion pura, sin red/DB), con mas casos
reales de los que ese test indirecto justificaba cubrir."""
from retrievers import detect_apps_from_text


def test_detecta_renting_por_palabras_clave_reales():
    assert 'renting' in detect_apps_from_text('quiero alquilar un equipo')
    assert 'renting' in detect_apps_from_text('cual es el precio de renta de este equipo')


def test_hallazgo_real_f8_del_baseline_terminos_de_producto_sin_palabra_clave_de_modulo_caen_a_shop():
    """AUDITORIA/RAG_SUPPORT_BASELINE.md hallazgo F-8: detect_apps_from_text()
    es un mapa de keywords fijo heredado de la era ChromaDB, nunca
    reevaluado desde la migracion a pgvector. Una consulta real y realista
    de un cliente sobre renting ("la disponibilidad de la escalera") NO
    contiene ninguna palabra del mapa de renting (['renta', 'alquiler',
    'equipo', 'equipment', 'wizard', 'RentalRequest', 'RentalPeriod']) --
    cae al default 'shop', un filtro de metadata INCORRECTO para esta
    consulta real. Confirmado empiricamente (no solo teorico) -- registrado
    aqui como hallazgo documentado, no corregido en esta mision (ampliar el
    diccionario de keywords es una decision de contenido/producto sobre que
    terminos cubrir, no un bug de una linea; requiere revisar las ~28
    entradas del mapa con criterio, no parchear una sola)."""
    assert detect_apps_from_text('cual es la disponibilidad de la escalera') == ['shop']


def test_detecta_shop_por_palabras_clave_reales():
    assert 'shop' in detect_apps_from_text('cual es el precio de este producto')
    assert 'shop' in detect_apps_from_text('tienen esta marca disponible')


def test_detecta_multiples_apps_cuando_la_consulta_los_menciona_a_todos():
    detected = detect_apps_from_text('quiero cotizar un servicio tecnico y tambien alquilar un equipo')
    assert 'technical_services' in detected
    assert 'renting' in detected


def test_query_sin_ninguna_palabra_clave_cae_al_default_shop():
    """Documentado explicito en el propio codigo real (retrievers.py:
    `detected or ["shop"]`) -- nunca deja `apps` vacio/None, que
    significaria "buscar en TODO el corpus" en vez de acotar."""
    assert detect_apps_from_text('asdf jklm zzz sin ningun termino real') == ['shop']


def test_deteccion_no_distingue_mayusculas():
    assert detect_apps_from_text('ALQUILAR UN EQUIPO DE RENTING') == detect_apps_from_text('alquilar un equipo de renting')
