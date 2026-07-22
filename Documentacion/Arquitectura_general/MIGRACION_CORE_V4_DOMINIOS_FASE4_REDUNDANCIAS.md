# CORE v4 — Arquitectura por Dominios: Fase 4 (Eliminación de Redundancias)

**Fecha:** 2026-07-12
**Resultado:** **No-op, confirmado por el usuario.**

## Justificación

El objetivo de esta fase ("Eliminar cualquier almacenamiento duplicado") ya fue cumplido por la
migración de `organization` ejecutada antes de iniciar el plan CORE v4 (`Company`, `Branding`,
`ContactInfo`, `SocialLink`, con eliminación real de `core.SiteBrandConfig`/
`CompanyContactInfo`/`FooterLink(social)` — ver
`MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md`).

La Fase 3 (Validación de Propiedad de Datos) no encontró ningún otro caso de **dato
almacenado dos veces**: sus 6 hallazgos (3.1-3.6) son de *patrón de acceso* (un dominio lee el
modelo de otro directamente en vez de vía su Selector), no de *almacenamiento redundante* — no
hay una segunda copia del dato en ningún lado, solo una forma de leerla que no pasa por la capa
de servicio esperada.

El único caso real de "lo mismo registrado en más de un lugar" es el hallazgo crítico de
Operaciones (4 máquinas de estado independientes para el mismo evento de negocio). Por
definición propia del usuario, **Fase 4 es sobre almacenamiento, Fase 5 es sobre reubicar
lógica de negocio y separar responsabilidades** — la consolidación de Operaciones encaja en
Fase 5, no aquí.

## Estado

**Fase 4: COMPLETA (no-op).** Confirmado con el usuario antes de cerrarla.

**Iniciando Fase 5** a continuación — dado el riesgo real de tocar datos operativos en vivo
(pedidos, servicios y rentas actualmente en curso), esta fase arranca con una **propuesta de
diseño sin ejecutar código todavía**, para acordar el enfoque antes de tocar nada.
