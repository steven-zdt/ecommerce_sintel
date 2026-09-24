"""
HARDENING F10/C3 -- huella (SHA-256) de los componentes cuyo cambio EXIGE re-ejecutar el benchmark (plan sec. 14.2).

Se calcula sobre el arbol de trabajo del repo (raiz = ecommerce_sintel/, se deduce de la ubicacion de este archivo, funciona tambien
montando el repo en /repo). `image_in_sync` compara los modulos horneados en la imagen del ADK (/app) con el repo: si la imagen esta
desactualizada, el reporte del runner no representa el codigo del arbol.
"""
import hashlib
import os
from pathlib import Path

ROOT = Path(os.environ.get("EVAL_REPO_ROOT") or Path(__file__).resolve().parents[2])

# componente -> globs relativos a ecommerce_sintel/
COMPONENTS = {
    "model": ["ai_engine/model_chain.py", "ai_engine_adk/model_runtime.py"],
    "prompt": ["ai_engine/agents/profiles/*.yaml", "ai_engine_adk/input_guard.py"],
    "agent": ["ai_engine/agents/__init__.py", "ai_engine/routing.py", "ai_engine_adk/sintel_root_workflow.py"],
    "tool": ["ai_engine/tools/*.py", "ai_engine_adk/sintel_adapter.py", "ai_engine_adk/idempotency.py", "ai_engine/permissions.py"],
    "rag": ["ai_engine_adk/sintel_rag_adapter.py", "ai_engine_adk/grounding.py", "ai_knowledge/services/selectors.py",
            "ai_knowledge/services/ingestion.py"],
    "embedding": ["ai_knowledge/services/embedding_service.py"],
    "retriever": ["ai_engine/retrievers.py"],
    "reranker": [],  # no existe hoy; si aparece un modulo, agregarlo aqui (el hash cambia y el gate lo exige)
    "memory_policy": ["customer_memory/services/policy.py", "ai_engine_adk/customer_memory_adapter.py"],
    "guards": ["ai_engine_adk/output_guard.py", "ai_engine_adk/public_response.py"],
}
# Variables de entorno que definen el modelo/embedding ACTIVOS (sin secretos: el chain solo lleva nombre|tipo|url|modelo). NO entran en la
# huella (cambian segun el contenedor que corre el runner); se registran en el reporte y el gate las compara contra el baseline.
RUNTIME_ENV = ["LOCAL_MODEL_CHAIN", "EMBEDDING_MODEL", "EMBEDDING_PROVIDER"]

# repo (relativo) -> nombre plano en la imagen /app
_IMAGE_FLAT = ["auth.py", "retrievers.py", "routing.py", "model_chain.py", "cost_control.py", "config.py", "observability.py",
               "rate_limit.py", "permissions.py"]


def _files(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        out.extend(p for p in sorted(ROOT.glob(pattern)) if p.is_file())
    return out


def runtime_env() -> dict:
    return {k: os.environ.get(k, "") for k in RUNTIME_ENV}


def _hash_files(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))  # CRLF/LF no debe cambiar la huella
        h.update(b"\0")
    return h.hexdigest()


def compute() -> dict:
    """{componente: sha256} solo de ARCHIVOS del arbol (independiente del contenedor donde corre)."""
    return {name: _hash_files(_files(patterns)) for name, patterns in COMPONENTS.items()}


def overall(components: dict) -> str:
    return hashlib.sha256("".join(f"{k}:{components[k]}" for k in sorted(components)).encode()).hexdigest()


def changed_components(current: dict, recorded: dict) -> list[str]:
    return sorted(k for k in set(current) | set(recorded) if current.get(k) != recorded.get(k))


def image_in_sync(app_dir: str = "/app") -> bool | None:
    """True/False si existe la imagen horneada en `app_dir`; None si no aplica (no estamos en el contenedor del ADK)."""
    app = Path(app_dir)
    if not (app / "sintel_root_workflow.py").exists():
        return None
    pairs = [(ROOT / "ai_engine" / n, app / n) for n in _IMAGE_FLAT]
    pairs += [(p, app / p.name) for p in sorted((ROOT / "ai_engine_adk").glob("*.py"))]
    for sub in ("tools", "agents", "capabilities"):
        for p in sorted((ROOT / "ai_engine" / sub).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                pairs.append((p, app / sub / p.relative_to(ROOT / "ai_engine" / sub)))
    for repo_file, image_file in pairs:
        if not repo_file.exists():
            continue
        if not image_file.exists() or image_file.read_bytes().replace(b"\r\n", b"\n") != repo_file.read_bytes().replace(b"\r\n", b"\n"):
            return False
    return True
