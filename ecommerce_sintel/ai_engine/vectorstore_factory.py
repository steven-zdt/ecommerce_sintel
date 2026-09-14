import logging
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from config import CHROMA_HOST, CHROMA_PORT, CHROMA_AUTH_TOKEN, CHROMA_COLLECTION

logger = logging.getLogger(__name__)


def get_vectorstore(embeddings: Embeddings) -> Chroma:
    client_settings = Settings(anonymized_telemetry=False)

    if CHROMA_AUTH_TOKEN:
        client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=client_settings,
            headers={"Authorization": f"Bearer {CHROMA_AUTH_TOKEN}"},
        )
        logger.info("[vectorstore] ChromaDB con auth token")
    else:
        client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=client_settings,
        )
        logger.info("[vectorstore] ChromaDB sin auth (modo desarrollo)")

    vectorstore = Chroma(
        client=client,
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
    )

    logger.info(
        "[vectorstore] ChromaDB conectado: %s:%d coleccion=%s",
        CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION,
    )
    return vectorstore
