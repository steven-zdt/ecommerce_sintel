"""
Ingesta inicial de documentos en ChromaDB.
Ejecutar una vez (o cuando cambien los specs/codigo):

    docker exec ecommerce_sintel_ai python bootstrap.py

O desde el host:
    python ai_engine/bootstrap.py
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bootstrap")

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    DOCS_SPECS_PATH, CODEBASE_PATH,
    INGESTION_BATCH_SIZE, CHROMA_COLLECTION,
)
from loaders import load_all_documents
from splitters import split_all
from embeddings_factory import get_embeddings
from vectorstore_factory import get_vectorstore


def run_ingestion():
    logger.info("=== Sintel AI Engine — Bootstrap de ingesta ===")
    logger.info("Docs path  : %s", DOCS_SPECS_PATH)
    logger.info("Code path  : %s", CODEBASE_PATH)
    logger.info("Collection : %s", CHROMA_COLLECTION)

    logger.info("[1/4] Cargando documentos...")
    raw_docs = load_all_documents(DOCS_SPECS_PATH, CODEBASE_PATH)
    logger.info("      Total raw docs: %d", len(raw_docs))

    logger.info("[2/4] Fragmentando (splitting)...")
    chunks = split_all(raw_docs)
    logger.info("      Total chunks: %d", len(chunks))

    logger.info("[3/4] Inicializando embeddings y vectorstore...")
    embeddings  = get_embeddings()
    vectorstore = get_vectorstore(embeddings)

    logger.info("[4/4] Ingesta en ChromaDB (batch=%d)...", INGESTION_BATCH_SIZE)
    total = len(chunks)
    for i in range(0, total, INGESTION_BATCH_SIZE):
        batch = chunks[i : i + INGESTION_BATCH_SIZE]
        vectorstore.add_documents(batch)
        done = min(i + INGESTION_BATCH_SIZE, total)
        logger.info("      Progreso: %d / %d (%.0f%%)", done, total, 100 * done / total)

    logger.info("=== Ingesta completada. %d chunks indexados. ===", total)


if __name__ == "__main__":
    run_ingestion()
