"""
HARDENING F11/C3 -- matriz de cobertura de DETECCION (informe, NO gate): categoria x mutacion -> detectadas/total.

    python ai_engine_adk/eval/redteam_matrix.py [--out ruta.md]      (dentro de la imagen del ADK con el repo montado; ver README)

Sirve para decidir con datos si una mejora del clasificador (p. ej. decodificar base64 antes de clasificar) vale la pena o si la defensa
estructural (cerca, precedencia, niveles de tool, guardia de salida) ya cubre esa mutacion. `detect_injection` es solo MONITOR.
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
if Path("/app/sintel_root_workflow.py").exists():
    sys.path.insert(0, "/app")

from eval import redteam as rt  # noqa: E402


def render() -> str:
    matrix = rt.detection_matrix()
    kinds = sorted({k for cell in matrix.values() for k in cell})
    lines = ["| categoria | " + " | ".join(kinds) + " |", "|---|" + "---|" * len(kinds)]
    for category in sorted(matrix):
        row = []
        for kind in kinds:
            hit, total = matrix[category].get(kind, [0, 0])
            row.append(f"{hit}/{total}" if total else "-")
        lines.append(f"| {category} | " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    text = render()
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
