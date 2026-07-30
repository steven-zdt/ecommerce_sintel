"""
agent_graph.py - Fase 8 de AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md

Estructura como nodos de grafo lo que hoy solo vive documentado en prosa
(ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md: "9 Agent Profiles", "29
Tools") -- no re-descubre nada, formaliza un inventario que ya es codigo real:

  - Node `Agent`   <- ai_engine/agents/profiles/*.yaml   (9 archivos reales)
  - Node `Tool`    <- ToolMetadata(name=...) en ai_engine/tools/*_tools.py
  - Edge `USES`    Agent -> Tool, desde la lista `herramientas:` de cada YAML
                    (dato real del propio archivo, no inferencia de nombre)
"""
import ast
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = Path(__file__).resolve().parent / "agents" / "profiles"
TOOLS_DIR = Path(__file__).resolve().parent / "tools"

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
    from knowledge_graph import Node

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
            file=f"ai_engine/agents/profiles/{profile['_file']}.yaml",
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


if __name__ == "__main__":
    profiles = load_agent_profiles()
    tools = load_tool_names()
    print(f"Agent profiles encontrados: {len(profiles)} -> {[p.get('name') for p in profiles]}")
    print(f"Tools encontradas: {len(tools)} -> {sorted(tools.keys())}")
