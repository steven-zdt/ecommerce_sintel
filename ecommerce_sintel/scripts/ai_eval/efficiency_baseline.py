"""
HARDENING F12/C1 -- medicion de eficiencia del modelo primario (Ollama/Qwen3.5-9B) contra el ADK de DESARROLLO.

LO EJECUTA EL USUARIO A MANO (regla del proyecto: el asistente no corre tests ni benchmarks). Usa GPU/modelo: cierra otros consumidores.
Solo biblioteca estandar. No toca produccion ni la BD.

    EVAL_JWT=<jwt de un usuario de PRUEBA de dev, con exp largo> AI_SERVICE_TOKEN=<opcional> \
    python scripts/ai_eval/efficiency_baseline.py --base-url http://localhost:8101 --runs 2 --num-ctx 4096 \
        --ollama http://localhost:11434 --out scripts/ai_eval/_out/efficiency.json

Por agente reporta (de las metricas F9 de /chat): llamadas al modelo por turno, tokens de entrada TOTALES y POR LLAMADA (promedio, el
techo real se acerca al ultimo), tokens de salida (incluye razonamiento), tok/s, latencia, y el MARGEN contra num_ctx. Tambien lee
/api/ps de Ollama (reparto CPU/GPU, contexto) y mide el cold start si se pasa --cold (hace `keep_alive=0` antes del primer turno).
Los mensajes son sinteticos. Con los p95 de aqui se fijan AI_AGENT_MAX_OUTPUT_TOKENS y se decide num_ctx / AI_MAX_CONTEXT_CHARS.
"""
import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request

# (agente esperado, mensaje, source)
PROMPTS = [
    ("SupportAgent", "Hola, necesito hablar con una persona por un reclamo", "customer"),
    ("SupportAgent", "Cuanto dura la garantia de las camaras?", "customer"),
    ("OrderAgent", "Donde esta mi pedido mas reciente?", "customer"),
    ("RentalAgent", "Que equipos de camara tienen disponibles para alquilar?", "customer"),
    ("PaymentAgent", "Mi pago con tarjeta fue rechazado, que hago?", "customer"),
    ("SalesAgent", "Quiero una cotizacion para instalar 4 camaras", "customer"),
    ("CatalogAgent", "Lista los productos de la categoria video vigilancia", "admin"),
    ("CatalogAgent", "Muestrame los detalles del producto mas reciente", "admin"),
]


def post(url, payload, headers, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode())
    return body, int((time.monotonic() - started) * 1000)


def ollama_ps(base):
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/api/ps", timeout=10) as resp:
            return json.loads(resp.read().decode()).get("models", [])
    except Exception as exc:  # noqa: BLE001
        return [{"error": type(exc).__name__}]


def percentile(values, pct):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, max(0, -(-pct * len(values) // 100) - 1))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8101")
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--num-ctx", type=int, default=4096, help="contexto efectivo del modelo (ollama ps -> CONTEXT)")
    ap.add_argument("--cold", action="store_true", help="descarga el modelo (keep_alive=0) y mide el primer turno")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    jwt = os.environ.get("EVAL_JWT", "")
    if not jwt:
        ap.error("falta EVAL_JWT (JWT de un usuario de PRUEBA de dev; para los casos source=admin, uno con is_staff)")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {jwt}"}
    if os.environ.get("AI_SERVICE_TOKEN"):
        headers["X-AI-Service-Token"] = os.environ["AI_SERVICE_TOKEN"]

    report = {"num_ctx": args.num_ctx, "ollama_ps_before": ollama_ps(args.ollama), "agents": {}, "turns": []}
    if args.cold:
        try:
            post(args.ollama.rstrip("/") + "/api/generate", {"model": os.environ.get("EVAL_MODEL", "qwen3.5:9b"), "keep_alive": 0},
                 {"Content-Type": "application/json"}, timeout=60)
            time.sleep(3)
        except Exception as exc:  # noqa: BLE001
            print("no se pudo descargar el modelo:", type(exc).__name__)

    for run in range(args.runs):
        for expected, message, source in PROMPTS:
            try:
                body, wall_ms = post(args.base_url.rstrip("/") + "/chat",
                                     {"message": message, "source": source, "channel": "web"}, headers)
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                report["turns"].append({"agent_expected": expected, "run": run, "error": type(exc).__name__})
                continue
            m = body.get("metrics") or {}
            calls = m.get("llm_calls") or 0
            tin, tout = m.get("llm_tokens_in") or 0, m.get("llm_tokens_out") or 0
            turn = {"agent_expected": expected, "agent": body.get("agent"), "run": run, "wall_ms": wall_ms, "llm_calls": calls,
                    "tokens_in_total": tin, "tokens_in_per_call": round(tin / calls) if calls else None, "tokens_out": tout,
                    "tokens_per_s": m.get("tokens_per_s"), "tool_calls": m.get("tool_calls"), "degraded": bool(m.get("engine_unavailable"))}
            report["turns"].append(turn)
            report["agents"].setdefault(body.get("agent") or expected, []).append(turn)
            print(f"{turn['agent']:<15} {wall_ms:>7} ms  calls={calls} in/call={turn['tokens_in_per_call']} out={tout} tok/s={turn['tokens_per_s']}")
    report["ollama_ps_after"] = ollama_ps(args.ollama)

    print("\nagente            turnos  p95 ms   in/llamada(max)  margen vs num_ctx   salida p95   tok/s medio")
    summary = {}
    for agent, turns in sorted(report["agents"].items()):
        ok = [t for t in turns if not t["degraded"]]
        per_call = [t["tokens_in_per_call"] for t in ok if t["tokens_in_per_call"]]
        outs = [t["tokens_out"] for t in ok]
        tps = [t["tokens_per_s"] for t in ok if t["tokens_per_s"]]
        row = {"turns": len(turns), "degraded": len(turns) - len(ok), "wall_p95_ms": percentile([t["wall_ms"] for t in ok], 95),
               "in_per_call_max": max(per_call) if per_call else None, "out_p95": percentile(outs, 95),
               "tok_s_mean": round(statistics.mean(tps), 1) if tps else None}
        row["ctx_margin_tokens"] = args.num_ctx - row["in_per_call_max"] if row["in_per_call_max"] else None
        summary[agent] = row
        print(f"{agent:<16} {row['turns']:>6} {str(row['wall_p95_ms']):>8} {str(row['in_per_call_max']):>16} {str(row['ctx_margin_tokens']):>18} "
              f"{str(row['out_p95']):>12} {str(row['tok_s_mean']):>12}")
    report["summary"] = summary
    print("\nNOTA: tokens de entrada POR LLAMADA es un promedio del turno; la ultima llamada (con los resultados de las tools) es la mayor. "
          "Un margen negativo o < 300 tokens indica riesgo de recorte silencioso por Ollama.")
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
