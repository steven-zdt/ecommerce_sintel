# WHITE_LABEL_MIGRATION_ROADMAP.md
Fase 30-46 — Plan de eliminación de hard-coding, migración controlada y roadmap final

Solo diseño — nada de esto se ha implementado. Cada fase futura, al ejecutarse, debe seguir la disciplina de la Fase 38: baseline → alcance pequeño → tests → doc → Knowledge Graph → verificación frontend/backend → compatibilidad → checkpoint.

## Fase 30 — Lista HARDCODED → CONFIGURABLE

| Hardcoded hoy | Configurable futuro |
|---|---|
| `"Sintel"` (legalDocs.js, Sidebar, AuthLayouts, footer copyright, useSeoStructuredData.js) | `organization.Company.trade_name` vía `appConfigStore` |
| `Company.trade_name` default `'Sintel'` | Default vacío/neutral, sin dato de negocio en el esquema |
| `FooterCTAConfig` defaults ("Sintel Technology", rutas /tienda //cotizar) | Defaults neutrales o `null` obligando a configurar antes de publicar |
| `ai_engine/action_graph.py` prompt "asistente de Sintel...Colombia" | Interpolación desde `OrganizationSelector.get_company()`/`get_contact_info()` |
| Colores hex en `<style scoped>` (~3100 ocurrencias) | `var(--landing-*)` alimentado por `ThemeConfig` runtime |
| `frontend/index.html` `<title>`/spinner | Inyección en build/SSR desde `organization.SeoSettings` |
| Rutas `/tienda`, `/servicios`, `/alquiler`, `/cotizar` siempre presentes | `ModuleDefinition.enabled` consultado por guard de router |
| `seed_renting_home_cards` (marcas Hikvision/Dahua/etc.) | Migración de limpieza + fixture opcional de demo separado del seed obligatorio |
| Contenido T&C/Privacidad en `legalDocs.js` | Modelo de contenido legal versionado (nuevo) |
| `core.enums` payment methods/roles fijos | Evaluar si deben ser catálogo editable o quedar como supuesto documentado de plataforma |

## Fase 31 — Migración de `organization`

Para cada modelo: **REUSE** (Company, Branding, ContactInfo, SocialLink, EmailSettings, DomainSettings, SeoSettings, LegalEntityInfo — todos se quedan tal cual, sin mover). **EXTEND**: agregar UI de panel (`/panel/organizacion`), quitar default `'Sintel'` de `Company.trade_name`, neutralizar seeds de `EmailSettings`/`DomainSettings`. No se identificó ningún caso que amerite **MOVE** o **DEPRECATE**. `organization` se convierte en el núcleo de Business Identity confirmando la Decisión 3 del [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md).

## Fase 32 — Migración de `core`

Permanece: `HomeConfig`/Content Builder, Enums (con nota de revisión), APIs públicas, adapters. Evoluciona: `site-config` (quitar fallback `'Sintel'`, agregar bloque `theme`), `home-feed` (agregar flag `enabled` consumible por router), `HomeModuleConfig` (evoluciona a Module Registry, ver Fase 29 del target). No romper contratos existentes sin adapter — cualquier campo nuevo se agrega como opcional/aditivo primero.

## Fase 33 — Migración del frontend

```
ACTUAL (hardcoded/default) → RUNTIME CONFIG (ya existe parcialmente)
    → CONFIGURATION STORE (appConfigStore, extender)
    → THEME TOKENS (nuevo, aplicar var(--..) en runtime)
    → FEATURE GATES (nuevo, guard de router por ModuleDefinition.enabled)
    → BUSINESS-DRIVEN NAVIGATION (ya existe vía NavbarLink/FooterGroup, solo falta eliminar fallbacks hardcoded)
```

No reconstruir el router — agregar un guard incremental. No reemplazar el Design System — extenderlo con inyección de tokens en runtime sobre la base ya existente en `landing-design-system.css`.

## Fase 34 — Migración del dashboard

Construir `/panel/organizacion` (no existe hoy) como nueva sección del dashboard, siguiendo el patrón Orchestrator ya usado en las ~40 secciones BUSINESS_CONFIGURATION existentes — decisión confirmada en Decisión 4 del decision record. Debe cubrir: Identity, Legal, Contact, Domains, SEO defaults, Social Links, y (cuando existan) Theme y Content legal.

## Fase 35 — Plan de datos

Confirmado: NO introducir `tenant_id` en esta etapa (Decisión 2). Primero Business Configuration completa y validada con un segundo negocio de prueba (Fase 40); multi-tenancy queda como roadmap separado y posterior si el producto lo requiere.

## Fase 36 — Plan de seguridad

Todas las superficies nuevas de configuración (Identity, Theme, Modules, Domains, Legal, Content) deben quedar detrás de `IsAdminUser`, igual que el resto de `organization`/`dashboard` hoy. Mantener el sistema de auditoría/seguridad existente (`security` app, `security-events` en dashboard) — cualquier cambio a estos campos debe quedar registrado igual que otros cambios administrativos.

## Fase 37 — Plan de compatibilidad

```
LEGACY (fallback 'Sintel', acceso directo dashboard→organization.SocialLink)
    ↓ ADAPTER (mantener el literal como fallback de ÚLTIMO nivel mientras se migra, no eliminar de golpe)
    ↓ NEW CONFIG (organization como única fuente, dashboard usa OrganizationSelector)
    ↓ DEPRECATION (marcar el acceso directo como deprecated en código/docs)
    ↓ REMOVAL (eliminar tras confirmar cero referencias, vía Knowledge Graph)
```

Nunca eliminar una configuración actual sin este camino completo.

## Fase 38 — Disciplina de migración controlada (aplica a cada fase F1-F13 abajo)

1. Baseline (git status/HEAD limpio)
2. Alcance pequeño (1 fase, pocos archivos)
3. Ejecutar tests
4. Actualizar documentación (`.AGENT`, `CLAUDE.md` de la app tocada)
5. Actualizar/consultar Knowledge Graph (ejecutar `audit` si el artefacto está desactualizado, ver Fase 3 de [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md))
6. Verificar frontend manualmente (browser, no solo tests)
7. Verificar backend (tests + smoke manual)
8. Mantener compatibilidad (Fase 37)
9. Checkpoint (commit descriptivo, no mezclar con otro trabajo en curso — recordar que el branch actual ya tiene ~710 líneas de cambios preexistentes no relacionados, ver [WHITE_LABEL_BASELINE.md](WHITE_LABEL_BASELINE.md))
10. Continuar a la siguiente fase

## Fase 39 — Business A / Sintel (snapshot antes de tocar identidad visible)

Antes de F9 (eliminación de hardcoding), crear un snapshot `BUSINESS_PROFILE_SINTEL` capturando: logo actual, colores actuales (extraídos del CSS estático), contenido actual (Home/Footer/AboutUs/legal), datos SEO actuales, datos legales actuales (incluyendo el placeholder sin resolver de razón social — debe resolverse con el negocio real antes o durante este snapshot), dominios actuales, navegación actual, módulos activos actuales (los 4 de `MODULE_META`). Este snapshot es el "Business A" de referencia — no se debe perder nada de esto durante la migración.

## Fase 40 — Business B de prueba ("Zapatería Nova")

No tocar producción. Perfil hipotético con módulos SHOP + SERVICES + RENTING:
- Shop: Zapatos, Botas, Sandalias
- Services: Limpieza, Restauración, Cambio de suela, Cambio de tacón
- Renting: Zapatos para eventos, Accesorios

Configurar identity/theme/modules/navigation/content usando exactamente los mismos modelos que Business A (`organization`, `core`, dashboard). Este es el criterio de aceptación real de F11 del roadmap.

## Fase 41-42 — Prueba de white-label / prueba de no-cambio-de-código

Éxito = Business A y Business B renderizan correctamente usando el mismo build de código, diferenciándose solo por datos de configuración. Cualquier punto donde Business B requiera editar Vue/Django/router/servicios base para funcionar se registra como `BUSINESS_AGNOSTIC_GAP` — se espera encontrar al menos: contenido legal (requiere el modelo nuevo de Fase 30), y potencialmente el prompt del AI Engine si no se completó su migración a interpolación dinámica.

## Fase 43 — Multi-Tenancy Gate

Ver Decisión 2 en [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md). Reabrir este gate solo después de F0-F12.

## Fase 44 — Impact Analysis

Antes de tocar cualquier archivo real de las fases F1-F13, ejecutar `python -m project_knowledge_graph.cli change-impact <archivo>` (o el comando equivalente) para los archivos de la lista P0/P1 del [WHITE_LABEL_GAP_MATRIX.md](WHITE_LABEL_GAP_MATRIX.md) — requiere primero refrescar el artefacto del grafo (`GRAPH_COVERAGE_GAP` señalado en la Fase 3 del catálogo de reglas de negocio).

## Fase 45 — Roadmap final de fases

| Fase | Contenido | Riesgo | Depende de |
|---|---|---|---|
| F0 | Audit (este documento y sus hermanos) | Ninguno (solo lectura) | — |
| F1 | Identity: quitar defaults `'Sintel'`, consolidar fallback, resolver placeholder legal de razón social | Bajo | F0 |
| F2 | Business Profile: extender `organization` (sin app nueva) | Bajo | F1 |
| F3 | Modules: Module Registry sobre `HomeModuleConfig`, guard de router | Medio | F2 |
| F4 | Theme: `ThemeConfig` + inyección runtime de CSS vars | Medio | F2 |
| F5 | Content: modelo de contenido legal versionado, migrar `legalDocs.js` | Alto (impacto legal, requiere validación de negocio real, no solo técnica) | F2 |
| F6 | Runtime Config: agregar `theme`/`modules.enabled`/`legal` a `site-config` | Bajo | F3, F4, F5 |
| F7 | Frontend: reemplazar ~95 puntos hardcoded, aplicar theme tokens, eliminar fallback silencioso "Sintel" | Alto (blast radius grande, cientos de archivos para hex, pero incremental) | F6 |
| F8 | Dashboard: construir `/panel/organizacion`, panel de Theme, panel de Legal | Medio | F1, F4, F5 |
| F9 | Hardcoding removal: limpiar seeds (`seed_renting_home_cards`, Meta verification code), fallback duplicado, `index.html` estático, prompt de `ai_engine` | Medio | F1-F8 |
| F10 | Business Profile migration: snapshot `BUSINESS_PROFILE_SINTEL` (Fase 39), validar cero pérdida de datos | Medio | F9 |
| F11 | Second-business test: "Zapatería Nova" (Fase 40) sin tocar producción | Bajo (aislado) | F10 |
| F12 | White-label certification: Fases 41-42, registrar cualquier `BUSINESS_AGNOSTIC_GAP` restante | Bajo | F11 |
| F13 | Multi-tenancy decision gate: reabrir Decisión 2 con datos reales de F0-F12 | N/A | F12 |

## Fase 46 — Riesgo y reversibilidad por fase

| Fase | Blast radius | Rollback | Downtime | Impacto frontend | Impacto backend | Impacto datos |
|---|---|---|---|---|---|---|
| F1 | Bajo (pocos archivos backend) | Trivial (revert commit) | Ninguno | Ninguno directo | Migración de datos (quitar default) | Baja — requiere decidir el dato real de razón social con el negocio |
| F2 | Bajo (dashboard, aditivo) | Trivial | Ninguno | Ninguno | Nueva UI, sin tocar modelos | Ninguno |
| F3 | Medio (router + backend) | Medio (revertir guard, dejar todo visible) | Ninguno si se despliega con flags apagados por defecto | Alto (afecta navegación real) | Medio | Ninguno |
| F4 | Medio (CSS runtime) | Fácil (quitar script de inyección) | Ninguno | Medio-alto (visual) | Bajo | Ninguno |
| F5 | Alto (contenido legal) | Difícil una vez publicado (implicaciones legales reales, no solo técnicas) | Ninguno técnico, pero requiere validación legal externa antes de publicar | Alto | Medio | Alto — dato sensible, requiere revisión humana/legal, no solo migración de código |
| F6-F9 | Medio-alto acumulado (cientos de archivos en F7) | Incremental por PR, cada uno reversible individualmente | Ninguno si se hace con feature flags | Alto en F7 | Medio | Bajo |
| F10-F12 | Bajo (aislado, no toca producción) | Trivial (es un profile de prueba) | Ninguno | Ninguno en producción | Ninguno en producción | Ninguno en producción |
| F13 | N/A (decisión, no código) | N/A | N/A | N/A | N/A | N/A |
