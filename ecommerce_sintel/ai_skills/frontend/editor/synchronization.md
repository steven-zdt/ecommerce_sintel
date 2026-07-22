---
description: Como se mantiene ai_skills/frontend sincronizado con el AI Engine (RAG) y con la doc maestra. Incluye el hallazgo de la reorganizacion 2026-07-11.
metadata:
  domain: editor
  last_audited: "2026-07-11"
---

# Synchronization — ai_skills/frontend <-> AI Engine <-> SSoT

## 1. Ubicacion canonica — REGLA CRITICA

Toda skill de frontend **debe vivir bajo `ecommerce_sintel/ai_skills/frontend/`** (esta carpeta),
**no** bajo `ai_skills/frontend/` en la raiz del repo.

Razon: `ai_engine/config.py` define `CODEBASE_PATH = "/workspace/ecommerce_sintel"` (el
subdirectorio Django, no la raiz del repo). El loader del RAG
(`ai_engine/loaders.py:283`, seccion "5. Skills de frontend") hace:

```python
skills_path = os.path.join(codebase_path, "ai_skills", "frontend")
```

con `glob="**/*.md"` recursivo — por eso la estructura por dominios (`architecture/`,
`design_system/`, etc.) SI se indexa correctamente, siempre que viva dentro de
`ecommerce_sintel/ai_skills/frontend/`.

Cualquier archivo creado en la raiz `ai_skills/frontend/` (fuera de `ecommerce_sintel/`) **no se
indexa nunca** en el RAG del AI Engine, aunque `ecommerce_sintel/frontend/CLAUDE.md` y otros docs
lo referencien con una ruta relativa `ai_skills/frontend/...` (esas rutas relativas se resuelven
desde dentro de `ecommerce_sintel/`, no desde la raiz del repo).

## 2. Hallazgo de la reorganizacion 2026-07-11

Antes de esta reorganizacion existian **dos carpetas `ai_skills/frontend/` con contenido
divergente**:

- Raiz del repo: 5 archivos "ricos" (`FRONTEND_SKILL.md`, `FRONTEND_UI_RULES.md`,
  `FRONTEND_OFFCANVAS_SKILL.md`, `FRONTEND_PROMPT_BASE.md`, `FRONTEND_COMPONENT_REGISTRY.md`),
  ultima edicion ~2026-06-26/06-11. **Nunca indexados** por el AI Engine (fuera de `CODEBASE_PATH`).
- `ecommerce_sintel/ai_skills/frontend/`: solo `FRONTEND_COMPONENT_REGISTRY.md`, pero **mas
  reciente y completo** (2026-07-07 — incluia landing/, `AvailabilityPill`, `RentingRequestList`,
  `ProfessionalsAdminList`, `useEnums`, `useAppConfigStore`, ausentes en la copia de raiz). Este
  si era indexado, y era el unico contenido de frontend que el AI Engine realmente veia.
- `ecommerce_sintel/frontend/CLAUDE.md` referenciaba `ai_skills/frontend/FRONTEND_SKILL.md`,
  `FRONTEND_UI_RULES.md` y `FRONTEND_OFFCANVAS_SKILL.md` como si existieran en
  `ecommerce_sintel/ai_skills/frontend/` — **no existian ahi**, eran enlaces rotos de facto.

Se resolvio fusionando el contenido mas reciente de ambas copias dentro de
`ecommerce_sintel/ai_skills/frontend/`, organizado por dominios. Los 5 archivos originales en
ambas ubicaciones se dejaron como **stubs de redireccion** (no se borraron, para no romper
referencias externas por nombre de archivo) apuntando a los archivos de dominio nuevos.

**Gap no resuelto, fuera de alcance de esta reorganizacion:** `ai_engine/loaders.py` no indexa
`ai_skills/drf/` (no hay una seccion equivalente a la "5. Skills de frontend" para DRF). Si se
decide indexarlo, es un cambio de codigo en `ai_engine/`, no de contenido de skills — requiere
decision explicita del usuario.

## 3. Regla de extension, nunca duplicacion

Antes de crear un archivo `.md` nuevo en cualquier dominio:

1. Buscar si el concepto ya esta cubierto en algun archivo existente del dominio correspondiente
   (tabla en [ai_frontend_editor.md](ai_frontend_editor.md#mapa-de-dominios-de-este-directorio)).
2. Si existe, **extenderlo** — agregar una seccion, no crear un archivo paralelo.
3. Si es genuinamente nuevo, crearlo en el dominio correcto y enlazarlo desde los archivos
   relacionados con `[texto](ruta/relativa.md)`.
4. Actualizar el `metadata.supersedes` o `metadata.last_audited` del frontmatter cuando se
   reemplaza o revisa contenido existente.

## 4. Reindexar tras cambios

El AI Engine no tiene watch automatico sobre `ai_skills/`. Tras agregar/modificar archivos aqui,
reindexar via el endpoint del AI Engine (ver `ai_engine/main.py`, endpoint `/ingest` o el proceso
de bootstrap completo si el cambio es estructural). Esto es responsabilidad de quien mantiene
`ai_engine/`, no se automatiza desde este directorio.

## Ver tambien

- [architecture_audit.md](architecture_audit.md) — checklist de auditoria (Fase 1/2 del editor)
- `ai_skills/drf/` en la raiz del repo — skills equivalentes de backend DRF, mismo patron de
  mantenimiento pero sin integracion RAG confirmada (ver gap arriba)
