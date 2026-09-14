# 26 — Auditoría Enterprise: Core (Fase 12)

> **Fase 12 completada y cerrada 2026-08-03** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[25](25_AUDITORIA_ORGANIZATION.md).

## Resultado: sin hallazgos accionables

Se investigó `core/models.py`, `core/api/views.py`, `core/api/internal_ai.py`,
`core/services/{selectors,commands}.py`, `core/signals.py`, `core/urls.py`,
`core/management/commands/` y la doc de arquitectura, buscando específicamente cualquier
relación entre `core/` y `support/` (modelos de horario/disponibilidad que soporte debería
consultar, modo mantenimiento que debería coordinarse con el widget, comandos que toquen datos de
soporte, referencias cruzadas de cualquier tipo).

**Conclusión: `core/` y `support/` operan en dominios completamente desacoplados.** Grep
recursivo de `support` sobre todo `core/` no arrojó ningún resultado — cero imports, cero
ForeignKeys, cero llamadas directas. `core/` hoy es exclusivamente configuración visual de
Home/footer/marcas (`HomeBanner`, `HomeModuleConfig`, `HomeCard`, `FooterGroup`,
`BrandSliderConfig`, `AboutUsConfig`, etc.) — el dato que en algún momento podría haber sido
relevante para soporte (`working_hours`, horario de atención) ya vive en
`organization.ContactInfo` desde la migración auditada en la [Fase 10](25_AUDITORIA_ORGANIZATION.md),
fuera del alcance de `core`. No existe ningún concepto de "modo mantenimiento" en todo el
proyecto — no es una omisión puntual, es una feature que simplemente no existe.

Dos ítems cosméticos (P4), sin relación con soporte y **no implementados en esta fase** por
decisión explícita del usuario (bajo valor, no accionables para el objetivo de la auditoría):
- `core/services/commands.py::HomeFeedSelector._get_limit()` hace 3 queries evitables (una por
  módulo Shop/Renting/Services) en vez de una consulta agregada — mitigado por cache de 5 min.
- `core/audit_queries.py` (script de auditoría manual, `exec(open(...).read())`, no se importa en
  runtime de Django) contiene emojis, violando la regla "Cero Caracteres Especiales en Código
  Python" del proyecto.

## Resumen ejecutivo

Fase de bajo valor incremental, confirmada como tal por el propio análisis antes de invertir en
implementación: `core` no tiene ninguna superficie de riesgo compartida con el módulo de soporte
omnicanal que es el objeto real de esta auditoría. Se documenta el resultado negativo para dejar
constancia de que el área fue efectivamente revisada, sin generar cambios de código.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-10 | Hechas — ver documentos 15-25 |
| 12 — Core | **Hecha (este documento) — sin hallazgos accionables, core/support desacoplados** |
| 13 | Hecha — ver [27](27_AUDITORIA_MARKETING.md) |
| 14-16 | Fuera de alcance de esta sesión |
