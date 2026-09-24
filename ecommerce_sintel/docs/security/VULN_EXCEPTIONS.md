# Excepciones de vulnerabilidades (HARDENING F16, plan sec. 20.2)

Cada hallazgo de `scripts/supply_chain/scan_vulns.sh` (Trivy, pip-audit, Bandit) que se decida **aceptar** se registra aqui. Sin fila = no aceptado.
Una excepcion caduca en su fecha de revision; pasada esa fecha vuelve a ser un hallazgo abierto.

| Fecha | Herramienta | ID (CVE / regla) | Componente y version | Severidad | Motivo por el que se acepta | Mitigacion aplicada | Revisar antes de | Aprobado por |
|---|---|---|---|---|---|---|---|---|
| _(vacio: aun no se ha ejecutado ningun escaneo)_ | | | | | | | | |

Reglas:
1. Solo se aceptan hallazgos **sin fix disponible** o cuyo camino de explotacion **no existe** en Sintel (explicarlo en "Motivo").
2. Critical/High con fix disponible en una dependencia directa **no** se aceptan: se actualiza (y se re-ejecuta el benchmark de F10 si toca modelo, ADK, LiteLLM o Ollama).
3. Bandit: los falsos positivos por regla (p. ej. `B608` en SQL parametrizado) se documentan una vez por regla y ruta.
