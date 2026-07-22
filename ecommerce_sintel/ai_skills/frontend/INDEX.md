# Sintel Frontend Skills — Indice

> Reorganizado por dominios el 2026-07-11. Esta es la ubicacion canonica: indexada por el AI
> Engine (`CODEBASE_PATH` = `ecommerce_sintel/`, ver
> [editor/synchronization.md](editor/synchronization.md)).

**Empieza por [FRONTEND_PROMPT_BASE.md](FRONTEND_PROMPT_BASE.md)** si vas a hacer cualquier tarea
de frontend — es el prompt copy-paste con la lectura obligatoria minima.

## Dominios

| Dominio | Que contiene |
|---|---|
| [architecture/](architecture/) | Stack, composables, routing, stores Pinia |
| [design_system/](design_system/) | Tokens, colores, tipografia, spacing, iconos |
| [components/](components/) | Offcanvas, tablas, forms, dialogs, cards — imports validos |
| [ux/](ux/) | Reglas transversales, accesibilidad, responsive, loading states, animaciones |
| [testing/](testing/) | Estado real de testing (gaps honestos, no inventados) |
| [editor/](editor/) | Persona de mantenimiento, sincronizacion, auditoria de deuda tecnica, framework enterprise-wide (Panel Admin = unica fuente autorizada) |

## Archivos raiz (compatibilidad)

- `FRONTEND_PROMPT_BASE.md` — vivo, prompt base actualizado
- `FRONTEND_SKILL.md`, `FRONTEND_UI_RULES.md`, `FRONTEND_OFFCANVAS_SKILL.md`,
  `FRONTEND_COMPONENT_REGISTRY.md` — stubs de redireccion a los dominios de arriba, mantenidos
  solo porque `frontend/CLAUDE.md` y otros docs `.AGENT` los referencian por nombre exacto.
