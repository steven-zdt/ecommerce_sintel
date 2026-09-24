"""
HARDENING F10/C2 -- runner del golden dataset. Produce UN reporte JSON (ver README.md).

Nivel 1 (deterministico, sin LLM), dentro de la imagen del ADK montando el repo (no toca produccion ni la BD):
    docker compose run --rm --no-deps -v "$PWD:/repo:ro" -e EVAL_REPO_ROOT=/repo -w /app sintel_ai_adk \
        python /repo/ai_engine_adk/eval/runner.py --tier l1 --out /tmp/l1.json
Nivel 2 (en vivo, Qwen en DEV, lento; SOLO con autorizacion del usuario): --tier live --base-url http://localhost:8101
    con EVAL_JWT (usuario de prueba) y opcionalmente AI_SERVICE_TOKEN en el entorno.
Casos con env=django solo corren con --env django (dentro del contenedor de Django); en el ADK se omiten.
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # ai_engine_adk/ al FINAL: solo para importar `eval.*`
_APP = os.environ.get("EVAL_ADK_PATH") or "/app"
if Path(_APP, "sintel_root_workflow.py").exists():
    sys.path.insert(0, _APP)  # se evalua el codigo HORNEADO en la imagen (fingerprint.image_in_sync garantiza que coincide con el repo)

from eval import evaluators, fingerprint, schema  # noqa: E402

SECURITY_CATEGORIES = {"G", "H", "I", "J"}


def _run_case(case, tier, ctx):
    kind = case["kind"]
    started = time.monotonic()
    try:
        if tier == "live":
            ok, detail, extra = evaluators.LIVE[kind](case["input"], case["expected"], ctx)
        else:
            ok, detail = evaluators.L1[kind](case["input"], case["expected"])
            extra = {}
    except ImportError as exc:  # un modulo que no se puede importar es un fallo del entorno, NO un caso "omitido" silencioso
        return {"status": "error", "detail": f"no se pudo importar {exc.name} (entorno incorrecto para este caso)"}
    except Exception as exc:  # noqa: BLE001 -- un evaluador roto es un fallo del caso, no del runner
        return {"status": "error", "detail": f"{type(exc).__name__}: {str(exc)[:160]}"}
    return {"status": "pass" if ok else "fail", "detail": detail, "ms": int((time.monotonic() - started) * 1000), **extra}


def build_report(cases, tier, env, only, limit, ctx):
    selected = [c for c in cases if c["tier"] == tier and c.get("env", "adk") == env and (not only or c["category"] in only)]
    if limit:
        selected = selected[:limit]
    results, failures, gaps, gaps_closed = {}, [], [], []
    per_cat: dict = {}
    for case in selected:
        res = _run_case(case, tier, ctx)
        results[case["id"]] = res
        cat = case["category"]
        bucket = per_cat.setdefault(cat, {"total": 0, "pass": 0, "fail": 0, "skipped": 0, "error": 0, "known_gap": 0, "critical_fail": 0})
        if res["status"] == "skipped":
            bucket["skipped"] += 1
            continue
        if case.get("known_gap"):
            bucket["known_gap"] += 1
            (gaps_closed if res["status"] == "pass" else gaps).append(case["id"])
            continue
        bucket["total"] += 1
        if res["status"] == "pass":
            bucket["pass"] += 1
        else:
            bucket["fail" if res["status"] == "fail" else "error"] += 1
            failures.append({"id": case["id"], "severity": case["severity"], "detail": res["detail"]})
            if case["severity"] == "critical":
                bucket["critical_fail"] += 1
    metrics = {}
    for cat, b in per_cat.items():
        metrics[f"{cat}.pass_rate"] = round(b["pass"] / b["total"], 4) if b["total"] else None
        metrics[f"{cat}.cases"] = b["total"]
    metrics["security.violations"] = sum(b["critical_fail"] for b in per_cat.values())
    metrics["security.violations_by_category"] = {c: b["critical_fail"] for c, b in per_cat.items() if b["critical_fail"]}
    lat = sorted(ctx.get("latencies", []))
    if lat:
        metrics["latency.p50_ms"] = lat[len(lat) // 2]
        metrics["latency.p95_ms"] = lat[min(len(lat) - 1, max(0, -(-95 * len(lat) // 100) - 1))]
        metrics["latency.mean_ms"] = int(statistics.mean(lat))
    components = fingerprint.compute()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tier": tier, "env": env,
        "fingerprint": fingerprint.overall(components), "components": components,
        "image_in_sync": fingerprint.image_in_sync(), "runtime_env": fingerprint.runtime_env(),
        "categories": per_cat, "metrics": metrics, "failures": failures,
        "known_gaps": gaps, "known_gaps_now_passing": gaps_closed,
        "min_cases_warning": sorted(c for c, b in per_cat.items() if b["total"] < schema.MIN_CASES_PER_CATEGORY),
        "results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["l1", "live"], default="l1")
    ap.add_argument("--env", choices=sorted(schema.ENVS), default="adk")
    ap.add_argument("--only", default="", help="categorias separadas por coma, ej. A,H")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--base-url", default="http://localhost:8101")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    cases = schema.load_dataset()
    if args.env == "django":
        import django

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings.development")
        django.setup()
    ctx = {"base_url": args.base_url, "jwt": os.environ.get("EVAL_JWT", ""), "service_token": os.environ.get("AI_SERVICE_TOKEN", "")}
    if args.tier == "live" and not ctx["jwt"]:
        ap.error("el nivel live requiere EVAL_JWT (JWT de un usuario de PRUEBA de DEV) en el entorno")
    only = {c.strip().upper() for c in args.only.split(",") if c.strip()}
    report = build_report(cases, args.tier, args.env, only, args.limit, ctx)
    text = json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    m = report["metrics"]
    print(f"F10 {args.tier}/{args.env} fingerprint={report['fingerprint'][:12]} image_in_sync={report['image_in_sync']}")
    for cat in sorted(report["categories"]):
        b = report["categories"][cat]
        print(f"  {cat} {schema.CATEGORIES[cat]:<18} pass={b['pass']}/{b['total']} fail={b['fail']} error={b['error']} "
              f"skipped={b['skipped']} known_gap={b['known_gap']}")
    print(f"  security.violations={m['security.violations']} known_gaps={report['known_gaps']} now_passing={report['known_gaps_now_passing']}")
    for f in report["failures"]:
        print(f"  FAIL {f['id']} [{f['severity']}] {f['detail']}")
    skipped = {}
    for cid, r in report["results"].items():
        if r["status"] == "skipped":
            skipped.setdefault(r["detail"], []).append(cid)
    for why, ids in skipped.items():
        print(f"  OMITIDOS ({len(ids)}): {why} -> {ids[:4]}")
    if report["min_cases_warning"]:
        print(f"  AVISO: categorias con menos de {schema.MIN_CASES_PER_CATEGORY} casos: {report['min_cases_warning']}")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
