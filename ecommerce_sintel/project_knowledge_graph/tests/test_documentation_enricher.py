"""
Unit tests puros (sin I/O, texto sintetico) para knowledge_graph/enrichers/
documentation.py -- Fase 8 "Documentation Graph", Site Knowledge Graph,
2026-08-10. Modelado sobre prosa real de renting/.AGENT/docs/
ARQUITECTURA_COMPLETA_RENTIG.md (referencias entre backticks a rutas de
archivo, `Clase.metodo()` y URLs de endpoint).
"""
from project_knowledge_graph.knowledge_graph.enrichers.documentation import (
    extract_doc_references,
)


def test_extract_doc_references_captures_file_paths_in_backticks():
    text = "El ViewSet vive en `dashboard/api/renting_catalog_views.py` y expone acciones."
    refs = extract_doc_references(text)
    assert refs["file_paths"] == ["dashboard/api/renting_catalog_views.py"]


def test_extract_doc_references_captures_symbol_refs_with_and_without_parens():
    text = (
        "`EquipmentReviewCommands.create_review()` valida el guard real, y "
        "tambien se usa `AvailabilityEngine.is_available`."
    )
    refs = extract_doc_references(text)
    assert refs["symbol_refs"] == ["AvailabilityEngine.is_available", "EquipmentReviewCommands.create_review"]


def test_extract_doc_references_captures_endpoint_urls_and_strips_trailing_slash():
    text = "`/api/v1/dashboard/equipment/{uuid}/marketing/` acepta GET, PUT, DELETE."
    refs = extract_doc_references(text)
    assert refs["endpoint_urls"] == ["/api/v1/dashboard/equipment/{uuid}/marketing"]


def test_extract_doc_references_deduplicates_repeated_mentions():
    text = (
        "`renting/services/commands.py` se usa aca. "
        "Y de nuevo `renting/services/commands.py` mas abajo."
    )
    refs = extract_doc_references(text)
    assert refs["file_paths"] == ["renting/services/commands.py"]


def test_extract_doc_references_ignores_prose_without_backticks():
    text = "El archivo renting/services/commands.py se menciona sin backticks, no cuenta."
    refs = extract_doc_references(text)
    assert refs["file_paths"] == []


def test_extract_doc_references_does_not_capture_shorthand_second_method():
    """Limitacion documentada: la forma abreviada real
    `` `EquipmentMarketingCommands.upsert()`/`.delete()` `` -- el segundo
    metodo (`.delete()`, sin nombre de clase) NO se captura, solo la
    referencia explicita `Clase.metodo`."""
    text = "`EquipmentMarketingCommands.upsert()`/`.delete()` maneja marketing."
    refs = extract_doc_references(text)
    assert refs["symbol_refs"] == ["EquipmentMarketingCommands.upsert"]
