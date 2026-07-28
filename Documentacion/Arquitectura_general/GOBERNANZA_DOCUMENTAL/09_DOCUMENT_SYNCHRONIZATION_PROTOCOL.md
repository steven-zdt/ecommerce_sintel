# 09 — Document Synchronization Protocol

> **Fase 10 de la Auditoría de Gobernanza Documental.** Formaliza (sin reemplazar) la "Regla de
> actualización" ya declarada informalmente en `IMPLEMENTATION_SUMMARY.md` y el checklist §16 de
> `.AGENT.md`. Documento aditivo — no cambia ningún proceso existente, lo hace explícito y
> verificable.

---

## 1. Disparadores obligatorios (cuándo correr este protocolo)

| Disparador | Documentos que DEBEN tocarse |
|---|---|
| Cambio estructural de código en una app (nuevo modelo, Command/Selector, endpoint, permiso, signal) | Doc de Nivel 2 de esa app (obligatorio) + `IMPLEMENTATION_SUMMARY.md` si el cambio afecta una sección cross-app (RBAC, rutas raíz, dashboard BFF, .env, infra) |
| App nueva creada | Doc de Nivel 2 nuevo + fila nueva en tabla de `.AGENT.md` Y `CLAUDE.md` (mismo commit) + fila nueva en `IMPLEMENTATION_SUMMARY.md` + entrada en `ecommerce/urls.py` reflejada en la sección "Rutas API raíz" de `IMPLEMENTATION_SUMMARY.md` |
| App renombrada (ej. `wompi` → `payment`) | Grep global de todos los niveles 0-2 por el nombre viejo — ver caso real §4 |
| Endpoint agregado/eliminado/movido de prefijo | Tabla de endpoints del doc de Nivel 2 correspondiente + `IMPLEMENTATION_SUMMARY.md` si está en la sección "Rutas API raíz" |
| Nuevo evento/signal/notificación cross-app | Doc de Nivel 2 de la app origen (sección de eventos) + doc de Nivel 2 de cada app consumidora (referencia) + [[04_EVENT_REGISTRY_GLOBAL]] |
| Nueva dependencia cross-módulo (import entre apps) | Doc de Nivel 2 de ambas apps (origen: "consumido por", destino: "depende de") + [[06_CROSS_MODULE_REGISTRY]] + verificar que no aparece ya en la lista de "Patrones no permitidos" de `.AGENT.md` §13 |
| Plan/fase (Nivel 3) completado | Copiar el resultado final al doc de Nivel 2 (no dejar el Nivel 3 como única fuente) — ver regla G1/G5 de [[08_ARCHITECTURE_GOVERNANCE_MANUAL]] |
| Ejecución de esta auditoría de gobernanza en el futuro | Repetir Fases 1-10 completas o solo las apps tocadas desde la última pasada (ver §5) |

---

## 2. Orden obligatorio de actualización (por disparador típico: cambio en una app)

```
1. Editar el código.
2. Actualizar <app>/.AGENT/docs/ARQUITECTURA_COMPLETA_<APP>.md
   - Agregar sección "## Cambios Recientes" al final (formato ya definido en
     IMPLEMENTATION_SUMMARY.md: fecha, qué cambió y por qué, archivos afectados, contrato de
     API si cambió).
   - Si el cambio invalida una afirmación existente en OTRA sección del mismo doc, corregirla
     in situ (no solo agregar al final) — la auditoría 2026-07-23 de IMPLEMENTATION_SUMMARY.md
     encontró que dejar solo el "changelog al final" sin corregir el cuerpo del documento es la
     causa #1 de desincronización real detectada (contradicciones internas).
3. Si el cambio toca un contrato cross-app (endpoint, evento, servicio consumido por otra app):
   actualizar la sección relevante en el doc de Nivel 2 de la app consumidora también.
4. Si el cambio está cubierto por una sección cross-app de IMPLEMENTATION_SUMMARY.md (RBAC, rutas
   raíz, dashboard BFF, Docker, .env): actualizarla ahí también, en el mismo commit.
5. Si el cambio agrega/renombra/elimina una app: actualizar .AGENT.md Y CLAUDE.md (tabla de
   routing) en el mismo commit — nunca uno sin el otro.
6. Si el cambio afecta un registro global de esta auditoría (Service/Event/API/Cross-Module):
   actualizarlo o marcarlo explícitamente como "desactualizado desde <fecha>" si no hay tiempo de
   resincronizar de inmediato (mejor una marca honesta que un registro silenciosamente stale).
```

---

## 3. Checklist de verificación previa a guardar cualquier cambio documental

(Reglas de consistencia ya pedidas por el usuario en el prompt original de esta auditoría —
formalizadas aquí como checklist operativo, no solo como lista de deseos)

- [ ] No introduce contradicciones con el doc de Nivel 2 dueño del dato (grep del nombre de
      modelo/endpoint/servicio en los otros 19 docs de Nivel 2 antes de afirmar algo sobre él).
- [ ] No duplica contenido que ya vive en otro documento con el mismo nivel de detalle (regla G2).
- [ ] No deja referencias rotas (rutas de archivo, anchors `[[nombre]]`, links relativos).
- [ ] No referencia una ruta de API que no exista en el `urls.py` real de la app (grep antes de
      escribir).
- [ ] No contradice el conteo de modelos/endpoints declarado en otra parte del mismo documento
      (caso real: `core` tuvo "9 modelos" congelado 3 migraciones después de que el conteo real
      subiera a 12 — ver IMPLEMENTATION_SUMMARY.md).
- [ ] No introduce un endpoint/servicio/evento con el mismo nombre que otro ya registrado en
      [[03_SERVICE_REGISTRY_GLOBAL]] / [[04_EVENT_REGISTRY_GLOBAL]] / [[05_API_REGISTRY_GLOBAL]]
      apuntando a algo distinto.
- [ ] No usa un nombre de app obsoleto (grep contra `apps.py` real — regla G4).
- [ ] Todos los documentos que el cambio tocó quedan mutuamente sincronizados (mismo estado final
      descrito en cada uno, sin una versión "más nueva" que otra sobre el mismo hecho).

---

## 4. Caso de estudio real: cómo se ve una desincronización no resuelta (referencia, no ficticio)

`ecommerce_sintel/.AGENT.md` §7.1 sigue nombrando la app de pagos `wompi` en su diagrama ASCII de
dependencias, mientras el resto del mismo archivo (§7.4, tabla de anti-patrones §13) y
`IMPLEMENTATION_SUMMARY.md` completo usan `payment` consistentemente y advierten explícitamente
"la app nunca se llamó `wompi` en el código". Es la prueba viva de por qué el paso 6 de §2
("grep global de todos los niveles 0-2") es obligatorio y no opcional: un rename de app aplicado
en 19 de 20 lugares sigue siendo una desincronización activa. Ver corrección propuesta (aditiva,
no aplicada aún) en [[01_VALIDACION_SINCRONIZACION]] hallazgo DOC-01.

---

## 5. Cadencia de re-auditoría de gobernanza (Fases 1-10 completas)

No hay una cadencia fija impuesta por el proyecto hoy. Recomendación (aditiva, requiere decisión
humana para adoptarse formalmente):

| Trigger | Alcance de re-auditoría |
|---|---|
| Cada vez que se cree una app nueva | Fase 1 (mapa) + Fase 3 (dependency graph) + fila nueva en Fases 4-7 |
| Cada ~2-4 semanas de desarrollo activo, o antes de un despliegue mayor | Repetir el patrón de verificación línea-por-línea ya usado en `IMPLEMENTATION_SUMMARY.md` v10 (2026-07-23): auditar contra código real, no solo re-leer docs entre sí |
| Cuando `docs/specs/` u otro sistema paralelo se detecte divergiendo de nuevo | Fase 8 (Knowledge Registry) enfocada solo en ese subconjunto |

---

## 6. Responsabilidad

Este protocolo no asigna dueños humanos individuales (el repo no declara un CODEOWNERS ni
similar) — la responsabilidad de mantenerlo es de quien ejecuta el cambio de código, reforzada por
el flujo obligatorio de `.AGENT.md` (que cualquier agente de IA debe seguir antes de tocar código)
y por el AI Engine, que carga los 20 documentos de Nivel 2 automáticamente y por lo tanto es tanto
el principal *beneficiario* de mantenerlos sincronizados como una fuente adicional de detección de
desincronización (respuestas incorrectas del AI Engine son una señal de doc desactualizado).

---

*Fin del paquete de 10 fases. Ver índice completo en [[README]] (o en el mensaje de cierre de esta
auditoría).*
