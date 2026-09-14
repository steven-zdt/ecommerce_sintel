import re
import logging
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
    Language,
)

logger = logging.getLogger(__name__)

MD_HEADERS_TO_SPLIT = [
    ("#",   "section"),
    ("##",  "subsection"),
    ("###", "rule"),
    ("####","subrule"),
]

MD_CHUNK_SIZE    = 1800
MD_CHUNK_OVERLAP = 300

PY_CHUNK_SIZE    = 2200
PY_CHUNK_OVERLAP = 200

VUE_CHUNK_SIZE    = 1600
VUE_CHUNK_OVERLAP = 150


def split_markdown_docs(docs: list[Document]) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=MD_HEADERS_TO_SPLIT,
        strip_headers=False,
        return_each_line=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MD_CHUNK_SIZE,
        chunk_overlap=MD_CHUNK_OVERLAP,
        separators=["\n\n", "\n", "```", " "],
        length_function=len,
    )

    result: list[Document] = []
    for doc in docs:
        try:
            header_chunks = header_splitter.split_text(doc.page_content)
            for hc in header_chunks:
                merged_meta = {**doc.metadata, **hc.metadata}
                sub_docs = char_splitter.create_documents(
                    [hc.page_content],
                    metadatas=[merged_meta],
                )
                result.extend(sub_docs)
        except Exception as exc:
            logger.warning("[splitters] Error splitting markdown %s: %s", doc.metadata.get("source"), exc)
            result.append(doc)

    logger.info("[splitters] Markdown: %d docs -> %d chunks", len(docs), len(result))
    return result


def split_python_docs(docs: list[Document]) -> list[Document]:
    py_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=PY_CHUNK_SIZE,
        chunk_overlap=PY_CHUNK_OVERLAP,
    )

    result: list[Document] = []
    for doc in docs:
        try:
            chunks = py_splitter.create_documents(
                [doc.page_content],
                metadatas=[doc.metadata],
            )
            result.extend(chunks)
        except Exception as exc:
            logger.warning("[splitters] Error splitting python %s: %s", doc.metadata.get("source"), exc)
            result.append(doc)

    logger.info("[splitters] Python: %d docs -> %d chunks", len(docs), len(result))
    return result


def split_vue_docs(docs: list[Document]) -> list[Document]:
    """
    Divide Vue SFCs (.vue) y archivos JS (composables, stores) en chunks.
    Intenta separar por bloques <template>, <script>, <style> para mantener
    la coherencia semántica de cada sección del SFC.
    """
    SFC_BLOCK_RE = re.compile(
        r'(<template[\s\S]*?</template>|<script[\s\S]*?</script>|<style[\s\S]*?</style>)',
        re.MULTILINE,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=VUE_CHUNK_SIZE,
        chunk_overlap=VUE_CHUNK_OVERLAP,
        separators=["\n\n", "\n", "  ", " "],
        length_function=len,
    )

    result: list[Document] = []
    for doc in docs:
        src = doc.metadata.get("source", "")
        is_vue = src.endswith(".vue")

        try:
            if is_vue:
                # Extraer bloques del SFC como chunks separados
                blocks = SFC_BLOCK_RE.findall(doc.page_content)
                if blocks:
                    for block in blocks:
                        block_type = "template" if block.startswith("<template") else \
                                     "script" if block.startswith("<script") else "style"
                        if block_type == "style":
                            continue  # Los bloques <style> no aportan contexto semántico
                        if len(block) <= VUE_CHUNK_SIZE:
                            result.append(Document(
                                page_content=block.strip(),
                                metadata={**doc.metadata, "vue_block": block_type},
                            ))
                        else:
                            sub_chunks = char_splitter.create_documents(
                                [block],
                                metadatas=[{**doc.metadata, "vue_block": block_type}],
                            )
                            result.extend(sub_chunks)
                else:
                    # SFC sin separación clara → chunk directo
                    sub_chunks = char_splitter.create_documents(
                        [doc.page_content],
                        metadatas=[doc.metadata],
                    )
                    result.extend(sub_chunks)
            else:
                # JS (composable, store, router) → chunks por carácter
                sub_chunks = char_splitter.create_documents(
                    [doc.page_content],
                    metadatas=[doc.metadata],
                )
                result.extend(sub_chunks)
        except Exception as exc:
            logger.warning("[splitters] Error splitting Vue/JS %s: %s", src, exc)
            result.append(doc)

    logger.info("[splitters] Vue/JS: %d docs -> %d chunks", len(docs), len(result))
    return result


def split_all(docs: list[Document]) -> list[Document]:
    md_docs  = [d for d in docs if d.metadata.get("language") == "markdown"]
    py_docs  = [d for d in docs if d.metadata.get("language") == "python"]
    vue_docs = [d for d in docs if d.metadata.get("language") in ("vue", "javascript")]
    other    = [d for d in docs if d.metadata.get("language") not in ("markdown", "python", "vue", "javascript")]

    chunks = (
        split_markdown_docs(md_docs)
        + split_python_docs(py_docs)
        + split_vue_docs(vue_docs)
        + other
    )
    logger.info("[splitters] Total chunks generados: %d", len(chunks))
    return chunks
