# 00 — Mapa de Dependencias Documentales

> **Fase 1 de la Auditoría de Gobernanza Documental.** Este documento NO es una fuente de verdad de
> arquitectura — es un mapa de qué documento depende de cuál, qué documento es SSoT y qué documento
> solo referencia. No modifica ni reemplaza ningún documento existente (política aditiva, ver
> [[09_ARCHITECTURE_GOVERNANCE_MANUAL]]).
>
> Generado: 2026-07-24. Ámbito: toda la documentación bajo `.AGENT/`, `Documentacion/`, `docs/`,
> `AUDITORIA/` y los `CLAUDE.md`/`.AGENT.md` de cada módulo.

---

## 1. Los 3 niveles documentales (confirmados contra el repo real)

```
NIVEL 0 — Punto de entrada obligatorio
  ecommerce_sintel/.AGENT.md
      - Reglas globales (Service Layer, RBAC, soft-delete, transacciones, Karpathy Principles)
      - Tabla "DOCUMENTOS DE REFERENCIA POR MODULO" (routing app -> doc de arquitectura)
      - Debe coincidir línea por línea con ecommerce_sintel/CLAUDE.md (mismo contenido, rol espejo)

  ecommerce_sintel/CLAUDE.md
      - Espejo resumido de .AGENT.md para el editor IA (tabla de routing + flujo de 6 pasos)
      - NO fuente de verdad propia — debe actualizarse EN EL MISMO CAMBIO que .AGENT.md

  ecommerce_sintel/MEMORY.md
      - Paso 2 del flujo obligatorio: continuidad de sesión, "qué se hizo recientemente"
      - Se autodeclara parcialmente obsoleto (línea 5): el historial Mayo-Junio 2026 no
        incorpora kyc/security/operations/dashboard/core/notifications/support — remite a
        IMPLEMENTATION_SUMMARY.md para eso

NIVEL 1 — Índice maestro / fallback cuando la app no se conoce de antemano
  Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md
      - Paso 3b del flujo de .AGENT.md
      - Mapa app-por-app con fecha de última sincronización real contra código
      - Secciones cross-app que NO viven en un solo módulo (RBAC, rutas API raíz, dashboard BFF,
        Operaciones post-pago, infraestructura Docker, variables .env)
      - Referencia de vuelta a .AGENT.md (ciclo cerrado documentado explícitamente en ambos)
      - NO debe llevar el mismo nivel de detalle que cada ARQUITECTURA_COMPLETA_<APP>.md — es
        resumen ejecutivo + verificación puntual, no la fuente primaria de cada dominio

NIVEL 2 — SSoT por dominio de negocio (una app = un documento dueño)
  <app>/.AGENT/docs/ARQUITECTURA_COMPLETA_<APP>.md   (20 apps, ver tabla §2)
      - Fuente de verdad EXCLUSIVA de su dominio: modelos, Commands/Selectors, endpoints,
        permisos, integraciones, frontend consumidor, testing, migraciones
      - Cargado automáticamente por el AI Engine en cada sesión

  <app>/CLAUDE.md  (existe en 14 de 20 apps — ver gap en §4)
      - Puntero corto: "leer primero ARQUITECTURA_COMPLETA_<APP>.md" + reglas específicas de la app
      - NO debe duplicar contenido del doc de arquitectura, solo enrutar hacia él

NIVEL 3 — Documentos especializados (históricos / bitácora, no se actualizan retroactivamente)
  <app>/.AGENT/docs/ADR_*.md            - decisiones arquitectónicas puntuales, fechadas
  <app>/.AGENT/docs/AUDITORIA_*.md      - auditorías puntuales, fechadas
  <app>/.AGENT/docs/FASE*_*.md          - bitácora de fases de un plan ya (o parcialmente) ejecutado
  <app>/.AGENT/*.md (sin /docs/)        - planes/resúmenes ejecutivos de refactors puntuales
  Documentacion/Arquitectura_general/MIGRACION_*_FASE*.md
      - Certificaciones de migraciones grandes (CORE v4, Organization) — auto-consistentes,
        registro histórico cerrado, NO requieren sincronización continua
  AUDITORIA/*.md (raíz del repo, 13 archivos)
      - Auditoría técnica general (seguridad/deuda técnica/rendimiento/BD), fechada 2026-07-16,
        referencia explícita a IMPLEMENTATION_SUMMARY.md v8 (hoy v10) — es un snapshot, no vive
  docs/.AGENT/*.md
      - Auditorías/guías CROSS-APP que no viven en un solo módulo (AI Engine, flujo venta-pago)
```

---

## 2. Tabla app -> documento SSoT (20 apps de negocio, verificada contra el filesystem real)

| App | Doc SSoT (Nivel 2) | CLAUDE.md propio | Docs Nivel 3 |
|---|---|---|---|
| accounts | `accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` | Sí | — |
| cart | `cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md` | Sí | — |
| core | `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` | **No** | — |
| dashboard | `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` | **No** (tiene `dashboard/.AGENT.md`, **archivo vacío, 0 líneas** — ver hallazgo DOC-08 en Fase 2) | — |
| ecommerce (base/settings) | `ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md` | Sí | — |
| inventory | `inventory/.AGENT/docs/ARQUITECTURA_COMPLETA_INVENTORY.md` | **No** | — |
| kyc | `kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md` | Sí | — |
| marketing | `marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md` | Sí | — |
| notifications | `notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md` | **No** | — |
| operations | `operations/.AGENT/docs/ARQUITECTURA_COMPLETA_OPERATIONS.md` | **No** | — |
| orders | `orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md` | Sí | — |
| organization | `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` | Sí (nota: dice "Fase 3 de 9", desactualizado — ver IMPLEMENTATION_SUMMARY.md tareas pendientes) | — |
| payment | `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` | Sí | ADR-001 + AUDITORIA_FASE0 + AUDITORIA_2026-07-03 + FASE2..FASE9 (10 docs históricos) |
| quotes | `quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md` | Sí | — |
| renting | `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` | Sí | — |
| security | `security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md` | Sí | — |
| shop | `shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md` | Puntero "ANTIGRAVITY.md (antes CLAUDE.md)" ubicado en `shop/.AGENT/docs/CLAUDE.md` — **única app con el puntero fuera de la raíz del módulo** (las demás lo tienen en `<app>/CLAUDE.md`) | `ANTIGRAVITY.md` |
| support | `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` | **No** | **Desactualizado** — no refleja endpoint CSAT ni AI Core (confirmado, ver Fase 2) |
| technical_services | `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` | Sí | AUDITORIA_FASE1_COMPLETA, PLAN_UNIFICACION_CON_RENTING, EXECUTIVE_SUMMARY, FASE2_* (5 docs) |
| users | `users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md` | Sí | — |
| frontend (transversal) | `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` | Sí | PHASE5..PHASE8, PLAN_MAESTRO_DESIGN_SYSTEM, PLAN_SINCRONIZACION (6 docs) |

**Apps sin `CLAUDE.md` propio (6 de 20):** `core`, `dashboard`, `inventory`, `notifications`, `operations`, `support`. Ninguna tabla de routing (`.AGENT.md`/`CLAUDE.md` raíz) lo exige como obligatorio — no es una inconsistencia per se, pero rompe la simetría del patrón "1 puntero corto + 1 doc completo" que sí siguen las otras 14. Ver recomendación en Fase 9.

---

## 3. Servicios fuera de `ecommerce_sintel/` con documentación propia

| Servicio | Doc principal | Rol |
|---|---|---|
| AI Engine (FastAPI :8100) | `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` | SSoT de arquitectura del motor (RAG, Tool Registry, Agent Profiles) |
| AI Engine — uso práctico | `ai_engine/.AGENT/GUIA_USO.md` | Complementario, no duplica FLIJO_COMPLETO |
| AI Engine — historia de fases | `ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md` | Nivel 3, bitácora de 8 fases cerradas |
| Guía de operación AI Engine (vista desde el resto del proyecto) | `docs/.AGENT/GUIA_AI_ENGINE.md` | Cross-app — cómo consultar/operar el AI Engine desde fuera |
| Auditoría cross-app checkout | `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md` | Cross-app — cart→orders→payment→notifications |

---

## 4. Sistema documental PARALELO detectado — `docs/specs/`

`docs/specs/` (13 archivos: `architecture_contracts.md`, `global_rules.md`, `cart.md`,
`dashboard_bff.md`, `frontend_vue.md`, `inventory.md`, `notifications.md`, `orders.md`,
`payment.md`, `renting.md`, `shop.md`, `technical_services.md`, `users_accounts.md`, `wompi.md`)
es un **segundo sistema de reglas/contratos de arquitectura**, independiente de `.AGENT.md` y de
los `ARQUITECTURA_COMPLETA_<APP>.md`, con formato YAML frontmatter propio (`app_name`, `layer`,
`doc_type`, `critical_rules`).

**No aparece referenciado en ninguna parte del flujo obligatorio de `.AGENT.md`** (sección "FLUJO
OBLIGATORIO ANTES DE MODIFICAR CÓDIGO") ni en `CLAUDE.md` ni en `IMPLEMENTATION_SUMMARY.md` — es
decir, existe fuera del ciclo de gobernanza documentado. Ver hallazgos detallados de contenido
desactualizado (app `wompi` en vez de `payment`, apps faltantes) en
[[01_VALIDACION_SINCRONIZACION]] §5 y [[07_KNOWLEDGE_REGISTRY]].

**Recomendación (no ejecutada en esta auditoría — aditiva, requiere decisión humana):** decidir si
`docs/specs/` se declara oficialmente obsoleto/superseded por `.AGENT.md` (con una nota en la
cabecera de cada archivo, sin borrar nada) o si se re-sincroniza. Ver Fase 9.

---

## 5. Relación de referencia (quién apunta a quién)

```
.AGENT.md  <---------------------->  IMPLEMENTATION_SUMMARY.md   (ciclo cerrado, documentado
   |                                         ^                     explícitamente en AMBOS lados)
   | tabla de routing                        | "paso 3b" cuando no se conoce la app
   v                                         |
ARQUITECTURA_COMPLETA_<APP>.md  <----(resume)-+
   |
   +--> ADR / AUDITORIA / FASE*.md   (bitácora, no se re-sincroniza)

CLAUDE.md (raíz)  ---(debe coincidir línea por línea, mismo commit)--->  .AGENT.md

MEMORY.md  ---(remite para detalle app-por-app)--->  IMPLEMENTATION_SUMMARY.md

docs/specs/*.md   (NO conectado al ciclo anterior — sistema paralelo, ver §4)

AUDITORIA/*.md (raíz)   ---(referencia puntual, snapshot fechado)--->  IMPLEMENTATION_SUMMARY.md v8
```

---

## 6. Consumidores automatizados

- **AI Engine**: carga automáticamente los `ARQUITECTURA_COMPLETA_<APP>.md` de cada app en cada
  sesión (declarado en `IMPLEMENTATION_SUMMARY.md` y `.AGENT.md`). Cualquier documento Nivel 2 que
  quede desactualizado degrada directamente las respuestas del AI Engine, no solo la documentación
  humana — esto eleva la prioridad de mantener sincronizados estos 20 documentos por encima de los
  de Nivel 3.

---

Ver siguiente: [[01_VALIDACION_SINCRONIZACION]] (Fase 2).
