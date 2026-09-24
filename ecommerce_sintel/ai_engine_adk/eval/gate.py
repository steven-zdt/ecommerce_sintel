"""
HARDENING F10/C3 -- regression gate. Solo INFORMA (exit code) hasta que se cablee a deploy.sh (decision pendiente del usuario).

    python ai_engine_adk/eval/gate.py --report l1.json [--report live.json] [--baseline eval/baselines/baseline_X.json]

Falla (exit 1) si:
  a) el fingerprint del arbol de trabajo difiere del del reporte (hubo un cambio de modelo/prompt/agente/tool/RAG/embedding/
     retriever/reranker/politica de memoria que el reporte no evaluo) o la imagen del ADK no coincide con el repo;
  b) una metrica `absolute` (seguridad) no cumple su valor;
  c) una metrica `ge_baseline` cae por debajo de la del baseline (si se da --baseline);
  d) el reporte contiene fallos de casos NO marcados como known_gap.
Metricas `slo` con valor null (p95) se omiten: se fijan con el primer baseline en vivo autorizado (F24).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval import fingerprint  # noqa: E402

DEFAULT_THRESHOLDS = Path(__file__).resolve().parent / "thresholds.json"


def merge(reports: list[dict]) -> dict:
    """Une reportes (p. ej. ADK + Django): las metricas se combinan y las violaciones de seguridad se SUMAN."""
    merged = {"metrics": {}, "failures": [], "fingerprints": {r["fingerprint"] for r in reports}, "components": {}, "image": []}
    for r in reports:
        merged["metrics"].update({k: v for k, v in r["metrics"].items() if k != "security.violations"})
        merged["failures"].extend(r.get("failures", []))
        merged["components"] = r["components"]
        merged["image"].append(r.get("image_in_sync"))
    merged["metrics"]["security.violations"] = sum(r["metrics"].get("security.violations", 0) for r in reports)
    return merged


def check(reports: list[dict], thresholds: dict, baseline: dict | None = None, current_components: dict | None = None) -> list[str]:
    problems: list[str] = []
    merged = merge(reports)
    current = current_components if current_components is not None else fingerprint.compute()
    if len(merged["fingerprints"]) > 1:
        problems.append("los reportes tienen fingerprints distintos entre si (se corrieron sobre codigo distinto)")
    changed = fingerprint.changed_components(current, merged["components"])
    if changed:
        problems.append(f"cambio SIN evaluar en: {', '.join(changed)} (volver a correr el benchmark)")
    if any(v is False for v in merged["image"]):
        problems.append("la imagen del ADK no coincide con el repo (reconstruir la imagen antes de evaluar)")
    if baseline:
        for r in reports:
            if r.get("tier") == "live" and baseline.get("runtime_env") and r.get("runtime_env") != baseline["runtime_env"]:
                problems.append("el modelo/embedding activo (LOCAL_MODEL_CHAIN/EMBEDDING_*) difiere del del baseline (re-baselinear)")
    for name, want in thresholds.get("absolute", {}).items():
        got = merged["metrics"].get(name)
        if got is not None and got != want:
            problems.append(f"{name}={got} (debe ser {want})")
    if baseline:
        for name in thresholds.get("ge_baseline", []):
            got, base = merged["metrics"].get(name), baseline["metrics"].get(name)
            if got is not None and base is not None and got < base:
                problems.append(f"{name} cayo: {got} < baseline {base}")
    for f in merged["failures"]:
        problems.append(f"caso fallido {f['id']} [{f['severity']}]")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="append", required=True)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    args = ap.parse_args(argv)
    reports = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.report]
    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8")) if args.baseline else None
    problems = check(reports, thresholds, baseline)
    if problems:
        print("GATE: FALLA")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("GATE: OK (informativo: aun no bloquea deploy.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
