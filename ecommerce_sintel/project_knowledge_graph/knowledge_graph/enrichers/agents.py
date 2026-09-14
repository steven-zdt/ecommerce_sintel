"""
Enricher: nodos Agent/Tool desde el AI Engine (Fase 5, PLAN_MAESTRO_DE_
SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08). Extraido de ai_engine/
agent_graph.py.

No re-descubre nada, formaliza como nodos de grafo un inventario que ya es
codigo real:
  - Node `Agent`   <- ai_engine/agents/profiles/*.yaml
  - Node `Tool`    <- ToolMetadata(name=...) en ai_engine/tools/*_tools.py
  - Edge `USES`    Agent -> Tool, desde `herramientas:` de cada YAML

[Nota de dependencia, Regla 1 del plan] Este es el UNICO punto donde
project_knowledge_graph lee (solo lectura, nunca importa Python) archivos de
ai_engine -- necesario para que el grafo represente los Agents/Tools reales.
Es una dependencia de datos en un solo sentido (KG -> archivos de ai_engine),
nunca al reves: ai_engine no depende de esto para funcionar.
"""
import re
from pathlib import Path

import yaml

_AI_ENGINE_DIR = Path(__file__).resolve().parents[3] / "ai_engine"
AGENTS_DIR = _AI_ENGINE_DIR / "agents" / "profiles"
TOOLS_DIR = _AI_ENGINE_DIR / "tools"
REPO_ROOT = Path(__file__).resolve().parents[4]

TOOL_NAME_RE = re.compile(r'ToolMetadata\(\s*\n?\s*name\s*=\s*["\'](\w+)["\']')


def load_agent_profiles() -> list[dict]:
    profiles = []
    if not AGENTS_DIR.exists():
        return profiles
    for yml in sorted(AGENTS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        data["_file"] = yml.stem
        profiles.append(data)
    return profiles


def load_tool_names() -> dict[str, str]:
    """Nombre real de la Tool (de ToolMetadata) -> archivo donde vive."""
    tools: dict[str, str] = {}
    if not TOOLS_DIR.exists():
        return tools
    for py_file in sorted(TOOLS_DIR.glob("*_tools.py")):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for m in TOOL_NAME_RE.finditer(text):
            tools[m.group(1)] = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
    return tools


def enrich_with_agents(kg) -> dict:
    from project_knowledge_graph.knowledge_graph.relations import Node

    profiles = load_agent_profiles()
    tool_files = load_tool_names()

    for name, file in tool_files.items():
        nid = f"tool:{name}"
        kg.add_node(Node(nid, "Tool", name, file=file))

    agent_count = 0
    uses_edges = 0
    unresolved_tools: set[str] = set()

    for profile in profiles:
        name = profile.get("name") or profile["_file"]
        nid = f"agent:{name}"
        kg.add_node(Node(
            nid, "Agent", name,
            file=f"ecommerce_sintel/ai_engine/agents/profiles/{profile['_file']}.yaml",
            meta={
                "description": profile.get("description"),
                "permisos": profile.get("permisos", []),
                "capacidades": profile.get("capacidades", []),
                "intents": profile.get("intents", []),
            },
        ))
        agent_count += 1

        for tool_name in profile.get("herramientas", []) or []:
            tool_nid = f"tool:{tool_name}"
            if tool_nid in kg.nodes:
                kg.add_edge(nid, tool_nid, "USES")
                uses_edges += 1
            else:
                unresolved_tools.add(tool_name)

    return {
        "agent_nodes": agent_count,
        "tool_nodes": len(tool_files),
        "agent_uses_tool_edges": uses_edges,
        "tools_referenced_but_not_found": sorted(unresolved_tools),
    }
