"""
graph_visualizer.py - Fase 5 de AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md

Exporta KNOWLEDGE_GRAPH.json a un archivo HTML autocontenido y navegable
(GRAPH_VIEW.html) -- sin levantar ningun servidor nuevo, sin tocar
docker-compose.yml, sin infraestructura adicional. Se abre directo en
cualquier navegador.

Usa vis-network via CDN (unica dependencia externa -- requiere internet para
renderizar, igual que cualquier libreria via CDN de este proyecto, p.ej.
Bootstrap en frontend/index.html). Los DATOS del grafo van embebidos inline
en el HTML (no hay llamada de red a datos, solo a la libreria de dibujo).

Uso: python ai_engine/graph_visualizer.py
Salida: ai_engine/GRAPH_VIEW.html
"""
import json
from pathlib import Path

KG_PATH = Path(__file__).resolve().parent / "KNOWLEDGE_GRAPH.json"
OUT_PATH = Path(__file__).resolve().parent / "GRAPH_VIEW.html"

# Un color por tipo de nodo -- suficiente para distinguir capas de un vistazo,
# no se persigue una paleta de marca (esto es una herramienta interna).
TYPE_COLORS = {
    "App": "#1f2937", "Model": "#2563eb", "Serializer": "#0891b2",
    "ViewSet": "#7c3aed", "Command": "#dc2626", "Selector": "#16a34a",
    "Signal": "#d97706", "Consumer": "#0d9488", "Task": "#be185d",
    "ManagementCommand": "#64748b", "Service": "#4338ca", "Permission": "#b91c1c",
    "Endpoint": "#059669", "FrontendView": "#f59e0b", "FrontendComponent": "#fb923c",
    "PiniaStore": "#eab308", "Composable": "#facc15", "Layout": "#a3a3a3",
    "Route": "#84cc16", "Documentation": "#94a3b8", "DockerService": "#0ea5e9",
    "Agent": "#ec4899", "Tool": "#f472b6",
}
DEFAULT_COLOR = "#9ca3af"


def build_html() -> str:
    if not KG_PATH.exists():
        raise FileNotFoundError(f"{KG_PATH} no existe -- correr auditor.py primero")
    kg = json.loads(KG_PATH.read_text(encoding="utf-8"))

    vis_nodes = [{
        "id": n["id"],
        "label": n["name"],
        "group": n["type"],
        "color": TYPE_COLORS.get(n["type"], DEFAULT_COLOR),
        "title": f"{n['type']} · {n['app'] or '-'} · {n['file'] or '-'}",
    } for n in kg["nodes"]]

    vis_edges = [{
        "from": e["source"], "to": e["target"], "label": e["label"], "arrows": "to",
    } for e in kg["edges"]]

    node_types = sorted(kg["stats"]["node_types"].keys())
    type_options = "\n".join(
        f'<option value="{t}">{t} ({kg["stats"]["node_types"][t]})</option>' for t in node_types
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Sintel Knowledge Graph — {kg['stats']['total_nodes']} nodos / {kg['stats']['total_edges']} aristas</title>
<script src="https://unpkg.com/vis-network@9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; background: #0b0f1a; color: #e5e7eb; }}
  #toolbar {{ padding: 10px 14px; display: flex; gap: 10px; align-items: center; background: #111827;
              border-bottom: 1px solid #1f2937; flex-wrap: wrap; }}
  #toolbar h1 {{ font-size: 14px; font-weight: 600; margin: 0 12px 0 0; color: #f9fafb; }}
  #toolbar input, #toolbar select {{ background: #1f2937; color: #e5e7eb; border: 1px solid #374151;
              border-radius: 6px; padding: 5px 8px; font-size: 13px; }}
  #network {{ width: 100%; height: calc(100% - 52px); }}
  #hint {{ font-size: 12px; color: #6b7280; }}
</style>
</head>
<body>
  <div id="toolbar">
    <h1>Sintel Knowledge Graph</h1>
    <input id="search" type="text" placeholder="Buscar nodo por nombre...">
    <select id="typeFilter">
      <option value="">Todos los tipos</option>
      {type_options}
    </select>
    <span id="hint">Click en un nodo para centrar su vecindario (profundidad 2)</span>
  </div>
  <div id="network"></div>

<script>
  const ALL_NODES = {json.dumps(vis_nodes, ensure_ascii=False)};
  const ALL_EDGES = {json.dumps(vis_edges, ensure_ascii=False)};

  const nodesDS = new vis.DataSet(ALL_NODES);
  const edgesDS = new vis.DataSet(ALL_EDGES);
  const container = document.getElementById('network');
  const data = {{ nodes: nodesDS, edges: edgesDS }};
  const options = {{
    nodes: {{ shape: 'dot', size: 10, font: {{ color: '#e5e7eb', size: 11 }} }},
    edges: {{ color: {{ color: '#374151', highlight: '#f59e0b' }}, font: {{ color: '#9ca3af', size: 9, strokeWidth: 0 }},
              smooth: {{ type: 'continuous' }} }},
    physics: {{ stabilization: {{ iterations: 150 }}, barnesHut: {{ gravitationalConstant: -12000 }} }},
    interaction: {{ hover: true, tooltipDelay: 100 }},
  }};
  const network = new vis.Network(container, data, options);

  function applyFilters() {{
    const q = document.getElementById('search').value.toLowerCase();
    const t = document.getElementById('typeFilter').value;
    const visibleIds = new Set();
    ALL_NODES.forEach(n => {{
      const matches = (!q || n.label.toLowerCase().includes(q)) && (!t || n.group === t);
      if (matches) visibleIds.add(n.id);
    }});
    nodesDS.update(ALL_NODES.map(n => ({{ id: n.id, hidden: !visibleIds.has(n.id) }})));
    edgesDS.update(ALL_EDGES.map(e => ({{
      id: e.from + '|' + e.to + '|' + e.label,
      hidden: !(visibleIds.has(e.from) && visibleIds.has(e.to)),
    }})));
  }}
  // vis-network necesita un id explicito por edge para poder actualizarlo -- se asigna una vez:
  ALL_EDGES.forEach(e => e.id = e.from + '|' + e.to + '|' + e.label);
  edgesDS.clear(); edgesDS.add(ALL_EDGES);

  document.getElementById('search').addEventListener('input', applyFilters);
  document.getElementById('typeFilter').addEventListener('change', applyFilters);

  network.on('click', function (params) {{
    if (params.nodes.length > 0) {{
      network.focus(params.nodes[0], {{ scale: 1.2, animation: true }});
    }}
  }});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    html = build_html()
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Escrito: {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")
