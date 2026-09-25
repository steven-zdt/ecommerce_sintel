# SLO - objetivos de servicio del asistente (HARDENING F24, 2026-09-25)

Estado: **PARCIAL / BLOCKED en los numeros de latencia y disponibilidad**. El plan (sec. 28) pide definirlos DESPUES del baseline en vivo y
`eval/thresholds.json` prohibe inventar numeros antes. El baseline en vivo no existe (ver `EVALUATION_BASELINE.md`: se detuvo porque el usuario
prohibe ejecutar benchmarks). Aqui quedan: (1) los SLO de seguridad, que el plan fija en 0; (2) la estructura y la fuente de cada SLO restante;
(3) lo unico observado hasta hoy, **como referencia y no como objetivo**.

## 1. SLO de seguridad (definidos por el plan, no dependen de medicion)
```yaml
slo:
  unauthorized_action_rate: 0        # tool de escritura ejecutada sin permiso o sin confirmacion requerida
  secret_leak_rate: 0                # secreto/infra/prompt en una respuesta publicada
  cross_user_data_leak_rate: 0       # dato o memoria de un cliente visible para otro
  prompt_injection_success_rate: 0   # inyeccion que cambia rol, permisos o ejecuta una accion
```
Fuente de medicion: `SecurityEvent` (`AI_SECURITY_FLAG`), `ai_tool_audit`, `memory_event`, red team (`eval/redteam.py`) y `eval/thresholds.json`
(`absolute.security.violations = 0`). Un valor distinto de 0 es un incidente (ver `INCIDENT_RESPONSE.md`), no un consumo de error budget.

## 2. SLO pendientes de baseline (numero = null hasta medir)
```yaml
slo:
  availability:            null   # % de turnos que reciben respuesta del asistente (no degradada). Fuente: ai_turn_metrics status != degraded
  latency_p95:             null   # ms por turno. Fuente: eval/thresholds.json slo.latency.p95_ms
  latency_p99:             null
  tool_error_rate:         null   # ai_tool_audit status != ok / total, excluyendo denied (403)
  fallback_rate:           null   # turnos servidos por LM Studio / total (breaker)
  human_handoff_time:      null   # segundos desde turno degradado hasta que un admin responde (F18: aviso a admins)
  incident_containment:    null   # minutos SEV1 -> kill switch (F21). Definir con el simulacro de F20
  error_budget:            null   # se deriva de availability una vez fijada
```

## 3. Lo observado (referencia, NO objetivo)
- Turno real medido en F9 (RentalAgent, 6 llamadas): 111 s, 12.1 tok/s; turnos tipicos 56-110 s (`MODEL_RUNTIME.md`). Con esa latencia un SLO
  de p95 razonable depende antes de F12/F13 (limites de salida, concurrencia) que de un numero elegido hoy.
- TTFT no existe: `/chat` no hace streaming. Si se quiere un SLO de TTFT hay que agregar streaming (fuera de este plan).
- `AI_TURN_MAX_SECONDS=120` es un tope tecnico de seguridad, no un SLO.

## 4. Como cerrar F24 (los comandos los corre el usuario, en dev)
1. `scripts/ai_eval/efficiency_baseline.py` (F12): latencia, tokens y tok/s por agente.
2. `scripts/load/adk_load_test.py --scenarios 1,5,10,20,50` (F13): p50/p95/p99, exito y timeouts por concurrencia.
3. `eval/runner.py` en modo live y guardar el baseline en `eval/baselines/`.
4. Con esos datos: fijar `slo.latency.p95_ms` en `eval/thresholds.json`, `AI_MAX_CONCURRENT_TURNS` y los numeros de la seccion 2, y pasar
   este documento a CLOSED. Hasta entonces F24 no se marca cerrada.
