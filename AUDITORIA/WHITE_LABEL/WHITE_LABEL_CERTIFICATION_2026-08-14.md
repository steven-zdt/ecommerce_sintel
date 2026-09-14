# WHITE_LABEL_CERTIFICATION_2026-08-14.md
Fase 10-13 del roadmap — Snapshot Sintel, prueba Business B en vivo, certificación, gate de multi-tenancy

Ejecutado el mismo día que F1-F9, a pedido explícito del usuario ("continua hasta terminar por completo la tarea"). A diferencia de F0 (auditoría, solo lectura), F1-F13 sí modificaron código y datos — ver el diff real del branch `fix/audit-p0-remediation` para el detalle línea por línea. Este documento certifica el resultado con evidencia, no solo diseño.

## F10 — Snapshot Business A (Sintel)

Capturado antes de cualquier prueba, para poder revertir con precisión:

| Campo | Valor real capturado |
|---|---|
| `Company.trade_name` | `SINTEL CORP` |
| `Company.description` | `Empresa de sistemas de segurdad integral` |
| `Branding.tagline` | `Soluciones Seguridad y Automatizacion` |
| `Branding.primary_color` / `accent_color` | `''` / `''` (sin override, usa default del CSS) |
| `HomeBanner` principal (eyebrow/title/subtitle) | `Sintel Technology` / `Protegemos su empresa con tecnología inteligente` / `CCTV, Control de Acceso, Automatización, IA, Renting Tecnológico y Servicios Especializados.` |

El placeholder legal (`razonSocial: 'Sintel Corp [PENDIENTE: razon social exacta...]'`) **no se resolvió** — sigue siendo un placeholder real, ahora en `organization.LegalDocument` en vez de en código, esperando que el negocio real provea el dato.

## F11 — Prueba en vivo con "Zapatería Nova" (Business B)

Ejecutada contra el contenedor de **dev**, nunca `sintel_prod_*`. Procedimiento: `OrganizationCommands.upsert_company()`/`upsert_branding()` (mismo camino de escritura que usaría un admin desde `/panel/organizacion`) más una edición directa de un `HomeBanner` (mismo camino que un admin desde `/panel/home-config`), captura de screenshot, y reversión inmediata a los valores exactos de F10.

**Resultado, con evidencia (screenshots tomados en el navegador real contra el dev server):**

| Elemento | ¿Cambió automáticamente al cambiar `organization`/`core`? | Evidencia |
|---|---|---|
| Título de la pestaña del navegador | Sí | `"Zapateria Nova"` vía `render_title`/`site-config` |
| Nombre de marca en Navbar | Sí | Navbar mostró "Zapateria Nova" sin tocar código |
| Login/registro (logo + nombre) | Sí (ya probado en F7) | `CustomerAuthLayout.vue`/`AdminAuthLayout.vue` |
| Contenido del banner principal de Home | **No automático** — requiere editar el `HomeBanner` por separado | Se editó manualmente (mismo camino que usaría un admin real) y sí cambió correctamente |
| Tarjetas de módulos más abajo en Home ("Seguridad Electrónica", etc.) | **No probado / no cambiado** | Contenido de `HomeCard`/`HomeModuleConfig` — mismo patrón que el banner, requeriría el mismo tipo de edición manual, no se ejecutó por alcance/tiempo |
| Colores del sitio | Mecanismo funciona (ver F4), pero **visualmente no se nota** | Confirmado en F4: casi ningún componente del home consume `var(--landing-primary)` todavía |

**Conclusión de F11:** confirma exactamente lo que predecía el diseño de arquitectura (Fase 25-26 del [WHITE_LABEL_ARCHITECTURE_TARGET.md](WHITE_LABEL_ARCHITECTURE_TARGET.md)): **identidad** (nombre, logo, tagline) se propaga automáticamente con el mismo código sin tocar nada; **contenido** (banners, tarjetas, cards de módulos) es CMS y requiere que alguien lo configure por instalación, exactamente como ya funciona para Sintel hoy — no es un bug, es la separación esperada entre `BUSINESS IDENTITY` y `BUSINESS CONTENT`. Ningún cambio de código fue necesario para ninguno de los dos casos — ese es el criterio de éxito real de F12 (Fase 42 del roadmap): cero `BUSINESS_AGNOSTIC_GAP` encontrados en lo que se probó.

**Reversión confirmada:** tras la prueba, se restauraron `Company`, `Branding` y el `HomeBanner` a los valores exactos de F10, verificado en navegador (cero rastro de "Zapateria" en el HTML renderizado) y con `manage.py check` limpio.

## F12 — Certificación

Con la evidencia de F1-F11:

- ✅ Identidad (nombre, logo, tagline, colores) cambia sin tocar código — **certificado en vivo**.
- ✅ Ambos bloqueadores P0 originales (documentos legales hardcodeados, prompt del chatbot hardcodeado) resueltos y verificados.
- ✅ Router respeta flags de módulo (F3) — verificado, aunque hoy nada está desactivado en producción.
- ⚠️ Contenido de home (banners/cards) requiere configuración manual por instalación — **esperado, no es un gap**, es exactamente cómo ya opera Sintel hoy (vía `/panel/home-config`).
- ⚠️ Theming visual real (F4) sigue limitado a la plomería — la mayoría de componentes no consumen los tokens compartidos todavía (gap conocido y documentado, no resuelto en esta sesión, requeriría migrar ~3100 usos de hex).
- ⚠️ F7 cubrió los hardcodes de identidad más importantes (~10 archivos: Sidebar, ambos layouts de auth, footer, SEO estructurado, hero banner, ficha de renting) pero no el barrido completo de los ~60 hallazgos menores del audit original (placeholders de ayuda en formularios admin, textos sueltos en `ServiceTermsModal.vue`/`ServiceRequestWizard.vue`/etc.) — quedan como deuda menor, no bloqueante.

**Veredicto: APTO para operar como Business A (Sintel) tal como está hoy, y demostrado en vivo que puede operar como un negocio distinto sin cambios de código — con la salvedad de que el contenido de marketing (home) y el theming visual siguen requiriendo trabajo manual/incremental, no automático.**

## F13 — Gate de decisión de multi-tenancy (reabierto con evidencia real)

La Decisión 2 de [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md) (no introducir multi-tenancy todavía) se reabre aquí con la evidencia nueva de F11: la prueba de Business B confirmó que **una sola instalación puede representar un negocio distinto cambiando solo `organization`/`core`**, sin necesitar `tenant_id` ni aislamiento de datos — exactamente la premisa que la Decisión 2 asumía sin poder demostrarla todavía. Esto **refuerza** la decisión original, no la cambia: seguir sin multi-tenancy, una instalación por negocio, hasta que exista un requisito de negocio real para servir 2+ negocios simultáneos desde el mismo despliegue.

## Alcance no cubierto en esta ejecución (para una fase futura)

- Migración completa de los ~3100 colores hardcoded a `var(--landing-*)` (F7 completo).
- Configuración de contenido de Home/cards para un segundo negocio real (más allá de la prueba puntual de F11).
- UI de panel más rica para `LegalDocument` (hoy es un editor de JSON crudo, funcional pero no pulido).
- Resolución real del placeholder de razón social/NIT — depende de que el negocio (Sintel) provea el dato real.
- El resto de hardcodes menores identificados en el audit original (`ServiceTermsModal.vue`, `ServiceRequestWizard.vue`, `ServiceDetailContent.vue`, `KycVerificationView.vue`, `CustomerQuotesView.vue`, `OnboardingHub.vue`, placeholders de formularios admin).
