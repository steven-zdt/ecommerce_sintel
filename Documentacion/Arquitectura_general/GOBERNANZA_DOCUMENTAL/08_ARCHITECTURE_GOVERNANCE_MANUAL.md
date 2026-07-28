# 08 — Architecture Governance Manual

> **Fase 9 de la Auditoría de Gobernanza Documental.** Este documento es ADITIVO: no reemplaza
> `ecommerce_sintel/.AGENT.md` (que sigue siendo la fuente de verdad operativa de reglas de código,
> cargada por el AI Engine y por el flujo obligatorio de consulta). Este manual consolida esas
> reglas por referencia (sin re-copiarlas, para no violar la regla anti-duplicación que él mismo
> establece) y agrega las reglas de **gobernanza documental** que hoy no están escritas en ningún
> lado del repo.

---

## 1. Principio rector

> Cada dominio de negocio es dueño exclusivo de su documentación. Ningún otro documento puede
> contener el mismo nivel de detalle sobre ese dominio — solo puede referenciarlo.

Esto ya rige implícitamente (`IMPLEMENTATION_SUMMARY.md` se autodeclara "no debe tener el mismo
nivel de detalle que los documentos específicos") pero no estaba formalizado como regla explícita
hasta este documento. Ver aplicación completa en [[07_KNOWLEDGE_REGISTRY]].

---

## 2. Reglas de código (YA VIGENTES — fuente de verdad: `ecommerce_sintel/.AGENT.md`)

No se repiten aquí en detalle para no duplicar la SSoT. Índice de a dónde ir por regla:

| Regla | Sección en `.AGENT.md` |
|---|---|
| Service Layer obligatorio (Commands escritura / Selectors lectura, ViewSets nunca tocan ORM) | §2 |
| Nomenclatura de modelos/serializers/métodos | §3 |
| API REST (URLs, códigos HTTP, paginación, filtros) | §4 |
| RBAC — permisos siempre desde `users.api.permissions`, nunca DRF directo | §5 |
| Modelos: soft-delete doble, slugs, snapshot pattern, índices, GenericFK con UUID | §6 |
| Integración entre módulos — mapa de dependencias de código, patrón Pull-Based (SummaryProvider), SSoT de Notificaciones/Pagos/Inventario/Precios | §7 |
| Transacciones y atomicidad, on_commit | §8 |
| Optimización de querysets (N+1, `.only()`, anotaciones en BD) | §9 |
| Reglas Vue.js (composables, `useApi()`, lazy loading) | §10 |
| Cálculos financieros (`Decimal`, centavos Wompi) | §11 |
| Celery | §12 |
| Patrones no permitidos (tabla anti-patrones) | §13 |
| Reglas críticas inventario/cupones/pagos | §14 |
| Karpathy Principles (ejecución de IA) | §15 |
| Checklists de módulo nuevo / componente Vue nuevo | §16-17 |
| Lecciones de auditoría (imports stale, `.annotate()` vs `@property`, `UniqueConstraint` + `instance=`, `@transaction.atomic` de alcance amplio, límite 30 chars en índices, tests en paralelo, falsos positivos de código muerto, Vite huérfano, `manage.py test` sin args excluye accounts/users, hard-delete vs PROTECT indirecto, `basename` vs path real, router DRF raíz sin sub-recurso) | §18 |

**[HALLAZGO — contradicción interna en `.AGENT.md`]** La sección §7.1 ("Dirección de Dependencias")
todavía dibuja el mapa de módulos usando el nombre de app `wompi` (`orders → wompi → SSoT de
PAGOS...`), mientras que la sección §7.4 del **mismo archivo** dice explícitamente "el módulo se
llama `payment`, no `wompi`" y el resto del documento (`.AGENT.md` completo) usa `payment`
consistentemente. Ver corrección propuesta (no aplicada, aditiva) en [[01_VALIDACION_SINCRONIZACION]]
hallazgo DOC-01 y en [[02_DEPENDENCY_GRAPH_GLOBAL]] (que sí usa el nombre correcto).

---

## 3. Reglas de gobernanza documental (NUEVAS — formalizadas por esta auditoría)

### G1. Jerarquía de 3 niveles es obligatoria para cualquier documento nuevo

Todo documento nuevo debe declararse explícitamente en uno de los 3 niveles de
[[00_MAPA_DEPENDENCIAS_DOCUMENTALES]] antes de crearse:
- Nivel 0 (reglas globales) — solo `.AGENT.md`/`CLAUDE.md`/`MEMORY.md`, no crear un cuarto punto de entrada.
- Nivel 1 (índice maestro) — solo `IMPLEMENTATION_SUMMARY.md`. Nunca agregarle detalle que ya vive
  en un doc de Nivel 2 — en su lugar, referenciar con link.
  Nunca agregarle detalle que ya vive en un doc de Nivel 2 — en su lugar, referenciar con link.
- Nivel 2 (SSoT de dominio) — un documento por app, ubicado en `<app>/.AGENT/docs/ARQUITECTURA_COMPLETA_<APP>.md`.
- Nivel 3 (histórico) — ADR/AUDITORIA/FASE, fechado, nunca se reescribe retroactivamente; si algo
  de un doc de Nivel 3 sigue vigente y no está en el Nivel 2, debe **copiarse** (no solo linkearse)
  al Nivel 2, porque el Nivel 3 puede archivarse sin previo aviso.

### G2. Una sola escritura de detalle, N referencias

Si dos documentos describen el mismo endpoint/modelo/regla con el mismo nivel de detalle, es una
violación de gobernanza (duplicación de conocimiento) aunque el contenido coincida hoy — porque
diverge con el primer cambio que solo se aplique en uno de los dos. Ver casos reales detectados en
[[07_KNOWLEDGE_REGISTRY]] (`docs/specs/` vs `.AGENT.md`/`ARQUITECTURA_COMPLETA_*`).

### G3. Todo documento de Nivel 2 declara su propia fecha de última verificación contra código

Patrón ya usado de facto por `IMPLEMENTATION_SUMMARY.md` ("Sincronizado 2026-07-09", "no releído
en esta pasada") — se formaliza aquí como regla obligatoria para los 20 docs de Nivel 2: cada uno
debe tener una línea visible cerca del encabezado con la fecha de última verificación real
línea-por-línea contra el código (no solo la fecha de última edición del archivo).

### G4. Ningún documento de Nivel 0/1 puede nombrar una app con un nombre que no sea el nombre real del paquete Python

Aplica en particular al caso `wompi` → `payment` (ver §2 arriba) y a cualquier app renombrada en
el futuro. Verificar contra `<app>/apps.py` antes de escribir un nombre de app en prosa.

### G5. Un documento de Nivel 3 declarado "plan" o "propuesta" no implica que esté implementado

Antes de asumir que un `PLAN_*.md`/`FASE*.md` representa el estado actual del código, confirmar
contra el doc de Nivel 2 correspondiente. Ver hallazgo sobre `PLAN_UNIFICACION_SERVICES_CON_RENTING.md`
en [[06_CROSS_MODULE_REGISTRY]] / [[01_VALIDACION_SINCRONIZACION]].

### G6. Simetría de puntero corto (`CLAUDE.md`) + documento completo

Patrón recomendado (no obligatorio hoy — 6 de 20 apps no lo siguen, ver
[[00_MAPA_DEPENDENCIAS_DOCUMENTALES]] §2): cada app debería tener `<app>/CLAUDE.md` como puntero
corto ("leer primero ARQUITECTURA_COMPLETA_<APP>.md" + reglas específicas de la app) ubicado en la
raíz del módulo — nunca anidado dentro de `.AGENT/docs/` (caso atípico: `shop`).

### G7. `docs/specs/` requiere una decisión de gobernanza explícita

No está conectado al flujo obligatorio de `.AGENT.md` y contiene contradicciones activas contra la
fuente de verdad actual (ver [[01_VALIDACION_SINCRONIZACION]] §5). Mientras no se tome una decisión
humana explícita (deprecar formalmente con nota en cabecera, fusionar, o resincronizar), **ningún
agente de IA debe usar `docs/specs/` como fuente de verdad si contradice `.AGENT.md` o un
`ARQUITECTURA_COMPLETA_<APP>.md`** — este es el criterio de desempate mientras se resuelve.

### G8. Todo cambio estructural de código dispara actualización del doc de Nivel 2 en el MISMO cambio

Ya declarado en `IMPLEMENTATION_SUMMARY.md` ("Regla de actualización") y en `.AGENT.md` (checklist
§16, ítem "Documento de arquitectura en `.AGENT/docs/`"). Se formaliza el protocolo completo en
[[09_DOCUMENT_SYNCHRONIZATION_PROTOCOL]].

### G9. Los registros globales (Fases 4-7 de esta auditoría) son derivados, no primarios

[[03_SERVICE_REGISTRY_GLOBAL]], [[04_EVENT_REGISTRY_GLOBAL]], [[05_API_REGISTRY_GLOBAL]] y
[[06_CROSS_MODULE_REGISTRY]] se reconstruyen a partir de los 20 documentos de Nivel 2 — no son
ellos mismos la fuente de verdad de ningún dato individual. Si diverge un registro global de su
doc de Nivel 2 origen, gana el doc de Nivel 2 y el registro global se marca desactualizado (no al
revés). Ver protocolo de resincronización en Fase 10.

---

## 4. Anti-patrones documentales prohibidos (equivalente documental de la tabla §13 de `.AGENT.md`)

| Prohibido | Alternativa correcta |
|---|---|
| Copiar el detalle de un doc de Nivel 2 dentro de `IMPLEMENTATION_SUMMARY.md` | Resumen de 1-3 líneas + link al doc de Nivel 2 |
| Crear un doc de reglas globales nuevo fuera de `.AGENT.md`/`CLAUDE.md` (ej. un tercer `RULES.md`) | Agregar la sección dentro de `.AGENT.md` (y espejarla en `CLAUDE.md`) |
| Editar retroactivamente un doc de Nivel 3 (ADR/AUDITORIA/FASE) para que "parezca" vigente | Si algo de ahí sigue vigente, copiarlo al doc de Nivel 2 con fecha de hoy |
| Dejar un `CLAUDE.md` de app con contenido que contradice su propio `ARQUITECTURA_COMPLETA_<APP>.md` | `CLAUDE.md` nunca declara hechos de arquitectura por sí mismo — solo enruta |
| Referenciar un nombre de app/endpoint sin verificar contra `apps.py`/`urls.py` real | Grep antes de escribir prosa (regla G4) |
| Dos documentos vivos describiendo el mismo evento/servicio/endpoint con el mismo detalle | Uno es dueño, el otro linkea (regla G2) |

---

Ver siguiente: [[09_DOCUMENT_SYNCHRONIZATION_PROTOCOL]] (Fase 10).
