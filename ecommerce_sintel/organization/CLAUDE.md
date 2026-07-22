# App: organization — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md
```

## Responsabilidad de esta app

**[EN CONSTRUCCION — Fase 3 de 9 completada, ver doc de arquitectura para el estado exacto.]**

SSoT (Single Source of Truth) de todo dato institucional/de empresa: branding, contacto,
correos, redes sociales, dominios, SEO, integraciones (credenciales de posteo en redes) e
informacion legal. Nace de una migracion planificada para eliminar la duplicidad de
configuracion de negocio que hoy vive repartida entre `core` (modelos) y
`ecommerce/settings/base.py` (credenciales via env vars).

Ver la auditoria completa que origino esta app en
`Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md`.

## Regla obligatoria: nadie consulta los modelos directamente

Ninguna otra app puede importar los modelos de `organization` ni leer `settings` para datos
institucionales. Toda lectura pasa por `OrganizationSelector` -> `OrganizationService`
(pendiente Fase 5). Sin signals, sin logica distribuida — la invalidacion de cache (si aplica)
se hace explicita en `OrganizationCommands`, no via `post_save`/`post_delete`.

## Reglas globales

Ver `.AGENT.md` en la raiz del proyecto.
