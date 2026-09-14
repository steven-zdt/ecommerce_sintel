"""
Fixture compartida: corre audit_full() una sola vez por sesion de tests (no
por test) -- es una corrida real contra el codigo real del repo (~21 apps,
~500 archivos frontend), no algo que valga la pena mockear (ver [[Feedback:
"no mockear la base de datos en tests de integracion"]] -- mismo criterio:
un mock del scanner no habria detectado el bug real de path resolution que
esta migracion encontro en agents.py/docker.py). Si PROJECT_MAP.json/
KNOWLEDGE_GRAPH.json ya existen y son de esta misma sesion de pytest, no se
reconstruyen dos veces.
"""
import pytest

from project_knowledge_graph.config import KNOWLEDGE_GRAPH_PATH, PROJECT_MAP_PATH


@pytest.fixture(scope="session")
def audited_project():
    from project_knowledge_graph.audit.auditor import audit_full

    if not (PROJECT_MAP_PATH.exists() and KNOWLEDGE_GRAPH_PATH.exists()):
        audit_full(verbose=False)
    return True
