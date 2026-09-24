"""
HARDENING F14/C1 -- simulacion de fallos (chaos) en DESARROLLO: detiene un componente, comprueba que el asistente degrada de forma
segura y que se recupera al volver. LO EJECUTA EL USUARIO A MANO (regla del proyecto: el asistente no corre tests ni benchmarks).

    EVAL_JWT=<jwt de un usuario de PRUEBA de dev> [AI_SERVICE_TOKEN=...] \
    python scripts/resilience/chaos_dev.py --base-url http://localhost:8101 --only ollama_down,redis_down --out scripts/resilience/_out/chaos.json

Seguridad: SOLO contenedores `ecommerce_sintel_*` (dev); se niega a tocar `sintel_prod_*` y a apuntar a produccion. Siempre reinicia lo que
detuvo (bloque finally), incluso con Ctrl+C. Avisa antes de empezar; los escenarios paran servicios compartidos de dev unos minutos.

Criterios por escenario (plan sec. 18): respuesta ACOTADA en el tiempo (no cuelga, no reintenta sin fin), degradacion segura con handoff
humano o respuesta real, SIN fuga (hosts internos, trazas, secretos) en el cuerpo, y RECUPERACION tras reiniciar. La ausencia de
corrupcion y de efectos duplicados no se puede observar desde fuera: se cubre con el test de idempotencia (fail-closed) y los logs.
LM Studio es una app del host: para "LM Studio down" cierralo a mano y usa --only lmstudio_manual (solo hace la sonda).
"""
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

DEV_PREFIX = "ecommerce_sintel_"
LEAK_MARKERS = ["sintel_ollama", "host.docker.internal", "Traceback", "/app/", ".env", "eyJ", "postgres://", "redis://"]
HANDOFF_MARKERS = ["agente humano", "no esta disponible", "mucha demanda"]

SCENARIOS = {
    # nombre: (contenedores a detener, esperado: 'ok_or_degraded' | 'fail_closed_auth', descripcion)
    "ollama_down": (["ecommerce_sintel_ollama"], "ok_or_degraded",
                    "Ollama caido: cae al fallback (LM Studio) o responde degradado con handoff, sin colgarse"),
    "redis_down": (["ecommerce_sintel_redis"], "ok_or_degraded",
                   "Redis degradado: rate limit/idempotencia/breaker fail-open; el chat sigue"),
    "postgres_down": (["ecommerce_sintel_db"], "ok_or_degraded",
                      "Postgres caido: sesiones del ADK y Django no disponibles; degrada o rechaza rapido, sin fuga"),
    "django_down": (["ecommerce_sintel_django"], "fail_closed_auth",
                    "Django caido: no se puede resolver la identidad -> el ADK falla CERRADO (401/5xx), nunca un turno anonimo"),
    "adk_restart": (["ecommerce_sintel_ai_adk"], "restart",
                    "Reinicio del ADK: tras volver, la misma conversacion sigue respondiendo (sesion persistente)"),
    "lmstudio_manual": ([], "ok_or_degraded", "LM Studio cerrado A MANO (solo sonda): el primario Ollama debe seguir respondiendo"),
}


def sh(*cmd, timeout=120):
    return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout)


def probe(args, jwt, message, conversation_id=None, timeout=240):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {jwt}", "X-Request-ID": f"chaos-{int(time.time() * 1000)}"}
    if os.environ.get("AI_SERVICE_TOKEN"):
        headers["X-AI-Service-Token"] = os.environ["AI_SERVICE_TOKEN"]
    body = json.dumps({"message": message, "conversation_id": conversation_id, "source": "customer", "channel": "web"}).encode()
    req = urllib.request.Request(args.base_url.rstrip("/") + "/chat", data=body, headers=headers, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        return {"status": 200, "ms": int((time.monotonic() - started) * 1000), "data": data}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "ms": int((time.monotonic() - started) * 1000), "data": {"detail": exc.read().decode()[:300]}}
    except Exception as exc:  # noqa: BLE001
        return {"status": 0, "ms": int((time.monotonic() - started) * 1000), "data": {"detail": type(exc).__name__}}


def leaks(res):
    text = json.dumps(res["data"], ensure_ascii=False)
    return [m for m in LEAK_MARKERS if m in text]


def wait_recovery(args, jwt, containers, max_wait=180):
    """Reinicia y espera a que /health del ADK y un turno real respondan."""
    for name in containers:
        sh("docker", "start", name)
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(args.base_url.rstrip("/") + "/health", timeout=5) as resp:
                if resp.status == 200:
                    break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3)
    time.sleep(10)  # deja levantar dependencias (db/redis) antes de la sonda de recuperacion
    return probe(args, jwt, "Hola, buenas tardes")


def run_scenario(args, jwt, name):
    containers, expectation, description = SCENARIOS[name]
    for c in containers:
        if not c.startswith(DEV_PREFIX):
            raise SystemExit(f"se niega a tocar {c}: solo contenedores de desarrollo ({DEV_PREFIX}*)")
    result = {"scenario": name, "description": description, "checks": {}}
    conv = f"chaos-{name}-{int(time.time())}"
    if expectation == "restart":
        result["pre"] = {"status": probe(args, jwt, "Hola, buenas tardes", conversation_id=conv)["status"]}
    try:
        for c in containers:
            sh("docker", "stop", c)
        time.sleep(5)
        res = probe(args, jwt, "Hola, necesito ayuda con mi pedido", conversation_id=conv if expectation == "restart" else None)
        result["during"] = {"status": res["status"], "ms": res["ms"], "degraded": bool((res["data"].get("metrics") or {}).get("engine_unavailable"))}
        limit_ms = (args.turn_max_seconds + args.queue_max_seconds + 20) * 1000
        result["checks"]["bounded_time"] = res["ms"] <= limit_ms
        result["checks"]["no_leak"] = not leaks(res)
        if expectation == "ok_or_degraded":
            text = (res["data"].get("response") or "").lower()
            result["checks"]["safe_answer_or_handoff"] = res["status"] == 200 and (
                bool(text) and (not result["during"]["degraded"] or any(m in text for m in HANDOFF_MARKERS)))
        elif expectation == "fail_closed_auth":
            result["checks"]["fails_closed"] = res["status"] in (401, 403, 500, 502, 503, 504) or (
                res["status"] == 200 and result["during"]["degraded"])
        elif expectation == "restart":
            result["checks"]["connection_error_or_ok"] = res["status"] in (0, 200, 502, 503)
    finally:
        rec = wait_recovery(args, jwt, containers)
    result["recovery"] = {"status": rec["status"], "ms": rec["ms"], "degraded": bool((rec["data"].get("metrics") or {}).get("engine_unavailable"))}
    result["checks"]["recovers"] = rec["status"] == 200 and not result["recovery"]["degraded"]
    if expectation == "restart":
        again = probe(args, jwt, "Gracias", conversation_id=conv)
        result["checks"]["same_conversation_continues"] = again["status"] == 200 and not (again["data"].get("metrics") or {}).get("engine_unavailable")
    result["passed"] = all(result["checks"].values())
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8101")
    ap.add_argument("--only", default="", help="escenarios separados por coma (default: todos menos lmstudio_manual)")
    ap.add_argument("--turn-max-seconds", type=int, default=120, help="AI_TURN_MAX_SECONDS del ADK")
    ap.add_argument("--queue-max-seconds", type=int, default=30, help="AI_QUEUE_MAX_WAIT_SECONDS si la admision esta activa")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    lowered = args.base_url.lower()
    if "sintel.net.co" in lowered or "sintel_prod" in lowered:
        ap.error("este script se niega a apuntar a produccion")
    jwt = os.environ.get("EVAL_JWT", "")
    if not jwt:
        ap.error("falta EVAL_JWT (JWT de un usuario de PRUEBA de dev)")
    names = [n.strip() for n in args.only.split(",") if n.strip()] or [n for n in SCENARIOS if n != "lmstudio_manual"]
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        ap.error(f"escenarios desconocidos: {unknown}; validos: {list(SCENARIOS)}")

    print("ATENCION: se van a detener contenedores de DESARROLLO uno por uno y se reiniciaran al terminar cada escenario.")
    report = []
    for name in names:
        print(f"\n== {name}: {SCENARIOS[name][2]}")
        res = run_scenario(args, jwt, name)
        report.append(res)
        for check, ok in res["checks"].items():
            print(f"   {'PASS' if ok else 'FAIL'}  {check}")
        print(f"   durante: {res.get('during')}  recuperacion: {res['recovery']}")
    print("\nRESUMEN:", ", ".join(f"{r['scenario']}={'OK' if r['passed'] else 'FALLA'}" for r in report))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
