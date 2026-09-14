"""
retrieve_knowledge_for_chat (retrievers.py) -- el fix del Bloque 4 (2026-08-08,
ver AI_SUPPORT_SCOPE.md seccion 6) + el fix de Knowledge Governance (Fase 17,
mismo dia): /chat nunca debe recibir codigo fuente (python/vue/javascript) NI
documentacion interna de ingenieria (aunque sea markdown) como "conocimiento"
para responderle a un cliente -- solo documentacion explicitamente
visibility="public".

Hallazgo real que motivo el segundo fix: una pregunta de cliente sobre "horario
de atencion" recupero un fragmento de ARQUITECTURA_COMPLETA_SERVICES.md (interno,
sobre agendamiento tecnico) y el LLM fabrico una respuesta de todos modos -- el
filtro anterior (solo language=="markdown") no distinguia entre eso y contenido
genuinamente apto para clientes.

No se puede levantar un ChromaDB real en esta suite -- se fake-ea el lado
semantico con un BaseRetriever real (misma interfaz que usa EnsembleRetriever
en produccion) devolviendo unicamente los docs que matchean el filtro del corpus
fake, para no depender de si la fusion BM25+MMR de Ensemble prioriza uno u otro:
el invariante que importa es que NINGUN doc no-publico puede aparecer en el
resultado, sin importar el ranking.
"""
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from retrievers import retrieve_knowledge_for_chat


class _FakeSemanticRetriever(BaseRetriever):
    docs: List[Document] = []

    def _get_relevant_documents(self, query, *, run_manager=None):
        return self.docs


class _FakeVectorStore:
    """Duck-types Chroma.as_retriever() lo suficiente para retrieve_knowledge_for_chat."""

    def __init__(self, all_docs: List[Document]):
        self._all_docs = all_docs

    def as_retriever(self, search_type=None, search_kwargs=None):
        flt = (search_kwargs or {}).get("filter") or {}
        conditions = flt.get("$and", [flt]) if flt else []
        matched = []
        for doc in self._all_docs:
            ok = True
            for cond in conditions:
                for key, op in cond.items():
                    if doc.metadata.get(key) != op.get("$eq"):
                        ok = False
            if ok:
                matched.append(doc)
        return _FakeSemanticRetriever(docs=matched)


def _corpus():
    return [
        Document(
            page_content="La garantia de los equipos de renting es de 12 meses.",
            metadata={"app_name": "renting", "doc_type": "faq", "language": "markdown", "visibility": "public"},
        ),
        Document(
            page_content="ProfessionalAvailability.check_time_availability valida conflictos de horario.",
            metadata={"app_name": "renting", "doc_type": "architecture", "language": "markdown", "visibility": "internal"},
        ),
        Document(
            page_content="class RentalRequest(models.Model): ...",
            metadata={"app_name": "renting", "doc_type": "model", "language": "python", "visibility": "internal"},
        ),
        Document(
            page_content="<template><RentingDetail /></template>",
            metadata={"app_name": "frontend_renting", "doc_type": "view", "language": "vue", "visibility": "internal"},
        ),
        Document(
            page_content="Reglas globales criticas: arquitectura service layer, soft-delete.",
            metadata={"app_name": "global_rules", "doc_type": "spec", "language": "markdown", "visibility": "internal"},
        ),
    ]


def test_retrieve_knowledge_for_chat_nunca_devuelve_codigo_fuente():
    vectorstore = _FakeVectorStore(_corpus())
    docs = retrieve_knowledge_for_chat(
        "como funciona la garantia del renting", vectorstore, _corpus(), apps=["renting"],
    )
    assert docs, "deberia devolver al menos el doc publico de garantia"
    for doc in docs:
        assert doc.metadata.get("language") == "markdown", (
            f"retrieve_knowledge_for_chat devolvio un doc no-markdown: {doc.metadata}"
        )


def test_retrieve_knowledge_for_chat_nunca_devuelve_doc_interno_aunque_sea_markdown():
    """Fase 17 (Knowledge Governance): el hallazgo real -- un doc de arquitectura
    interna (markdown, del mismo app_name, semanticamente parecido) NUNCA debe
    aparecer, solo por ser markdown. Solo visibility=="public" califica."""
    vectorstore = _FakeVectorStore(_corpus())
    docs = retrieve_knowledge_for_chat(
        "como funciona la garantia del renting", vectorstore, _corpus(), apps=["renting"],
    )
    for doc in docs:
        assert doc.metadata.get("visibility") == "public", (
            f"retrieve_knowledge_for_chat devolvio un doc no-publico: {doc.metadata}"
        )
    contents = [d.page_content for d in docs]
    assert not any("check_time_availability" in c for c in contents)


def test_retrieve_knowledge_for_chat_no_incluye_reglas_globales_fijas():
    """Esta funcion NO debe inyectar el bloque fijo de reglas globales de
    arquitectura backend en cada respuesta -- ese bloque es irrelevante para
    un cliente."""
    vectorstore = _FakeVectorStore(_corpus())
    docs = retrieve_knowledge_for_chat(
        "como funciona la garantia del renting", vectorstore, _corpus(), apps=["renting"],
    )
    contents = [d.page_content for d in docs]
    assert not any("service layer" in c for c in contents)


def test_retrieve_knowledge_for_chat_vacio_si_no_hay_contenido_publico():
    """Si no existe ningun doc publico para el app detectado, debe devolver vacio
    -- preferible a inventar con documentacion interna disponible."""
    corpus_sin_publico = [d for d in _corpus() if d.metadata.get("visibility") != "public"]
    vectorstore = _FakeVectorStore(corpus_sin_publico)
    docs = retrieve_knowledge_for_chat(
        "como funciona la garantia del renting", vectorstore, corpus_sin_publico, apps=["renting"],
    )
    assert docs == []
