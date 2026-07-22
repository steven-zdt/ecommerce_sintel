# CORE v4 — Arquitectura por Dominios: Fase 2 (Rediseño del Panel Administrativo)

**Fecha:** 2026-07-12
**Alcance:** Solo diseño de navegación. **Cero cambios de código en esta fase** — ni backend
ni frontend. El entregable es el mapa nuevo; la implementación real (mover archivos, editar
`router.js`/`Sidebar.vue`) es Fase 6 ("Refactorización del Frontend"), no esta.
**Decisiones base** (confirmadas por el usuario antes de iniciar esta fase, ver Fase 1):
Ventas = agrupación de menú únicamente (sin fusión de apps); Integraciones = solo en
Organization; kyc → Configuración; support (chat) → dominio propio "Soporte"; portafolio
profesional de `accounts` → nuevo dominio "Proveedores/Contratistas".

---

## 1. Inventario de la navegación actual (línea base real, no supuesta)

**Router:** `frontend/src/apps/admin/router.js` — 35 rutas bajo `/panel/*`.
**Sidebar:** `frontend/src/components/layout/Sidebar.vue` — 3 secciones hardcodeadas en JS
(`mainLinks`, `moduleGroups`, `systemLinks`), **no dirigido por permisos server-side**.

**Hallazgos de la línea base (independientes de la reorganización, se documentan para no
perderlos):**
- El sidebar es 100% estático en `<script setup>` — no hay un endpoint de menú ni
  permission-driven rendering. No es un problema de esta fase, pero condiciona cómo se
  implementará el cambio en Fase 6 (edición directa de arrays JS, no de datos).
- **7 rutas existen sin ningún item de menú que las enlace** (solo alcanzables por URL directa
  o links internos de otras vistas): `/panel/soporte`, y las 6 rutas de detalle
  (`ordenes/:uuid`, `renta/:uuid`, `cotizaciones/plantillas/:uuid`, `validaciones/:uuid`,
  `operaciones/:uuid`, `servicios/asignacion-tecnicos`). De estas, `/panel/soporte` es la única
  que **debería** tener un item de menú propio y no lo tiene — bug de navegación preexistente,
  no introducido por esta migración.
- **No existe ninguna ruta de Inventario en el panel** (`inventory` no tiene ni componente ni
  entrada de menú, pese a ser la SSoT de stock de todo el proyecto). Es un hueco de UI real,
  independiente de la reorganización por dominios — no se resuelve en esta fase (no es
  "reorganizar nav existente", sería construir UI nueva, fuera de alcance de Fase 2).
- **`organization` no tiene ninguna vista, módulo ni ruta en el frontend todavía** — confirmado
  por búsqueda exhaustiva. Se refleja en el nuevo mapa como pendiente de construir.

---

## 2. Nuevo mapa de navegación por dominios (15 dominios)

Formato: dominio → items del menú → **ruta actual sin cambios** (Fase 2 no renombra rutas,
solo reagrupa visualmente) → origen real (para que en Fase 6 se sepa qué mover y qué crear).

### PANEL (fijo, no es un dominio de negocio)
| Item | Ruta |
|---|---|
| Dashboard | `/panel/dashboard` |
| Mi Perfil | `/panel/perfil` |

### 1. Organization 🆕
| Item | Ruta | Estado |
|---|---|---|
| Empresa y Branding | *(no existe)* | 🆕 por crear — backend ya tiene `Company`/`Branding` con Selector/Commands (Fase 5 de la migración anterior) |
| Contacto y Redes Sociales | *(no existe)* | 🆕 por crear — backend ya tiene `ContactInfo`/`SocialLink` |
| Correos | *(no existe)* | 🆕 por crear — backend ya tiene `EmailSettings` |
| Dominios y SEO | *(no existe)* | 🆕 por crear — backend ya tiene `DomainSettings`/`SeoSettings` |
| Información Legal | *(no existe)* | 🆕 por crear — backend ya tiene `LegalEntityInfo` |
| Integraciones | *(no existe)* | 🆕 por crear — backend ya tiene `get_integration_settings()` (fachada de solo lectura sobre `.env`) |

> Es el único dominio donde Fase 2 no puede "reorganizar" nada existente — todo el backend
> (Fase 4/5 de la migración `organization`) ya está listo, pero el panel nunca tuvo UI. La
> gestión de Empresa/Contacto/Redes Sociales sigue temporalmente en **Sitio Web → Home Pública**
> (tabs Marca/Footer de `HomeConfigView.vue`) hasta que se construya esta sección — ver
> hallazgo 4.1.

### 2. Sitio Web (antes disperso entre "Marketing" y home-config)
| Item | Ruta actual | Origen |
|---|---|---|
| Home Pública (banners, tarjetas, módulos, CTA, navbar-estructura, footer-estructura) | `/panel/home-config` | Se queda igual — es contenido puro de `core`, ya no mezcla datos institucionales (migración previa) |

### 3. Catálogo (antes "Tienda")
| Item | Ruta actual |
|---|---|
| Productos | `/panel/productos` |
| Categorías | `/panel/categorias` |
| Marcas | `/panel/marcas` |
| Impuestos | `/panel/impuestos` |

> **Reubicación respecto al menú actual:** "Operaciones" (`/panel/productos/operaciones`,
> `ShopOperationBoard.vue`) **sale** de este grupo — es fulfillment/logística de pedidos, no
> catálogo. Ver dominio 11 (Operaciones).

### 4. Servicios
| Item | Ruta actual |
|---|---|
| Servicios | `/panel/servicios` |
| Categorías | `/panel/s-categorias` |
| Niveles | `/panel/s-niveles` |

> **Reubicaciones:** "Operaciones de Servicios" y "Asignación de Técnicos" salen a Operaciones
> (dominio 11). "Profesionales" sale a Proveedores/Contratistas (dominio 13) — hoy vive aquí
> por conveniencia histórica, pero es CV/portafolio de personas, no catálogo de servicios.

### 5. Renting
| Item | Ruta actual |
|---|---|
| Equipos | `/panel/renta` |
| Solicitudes | `/panel/renta/solicitudes` |
| Categorías | `/panel/r-categorias` |
| Marcas | `/panel/r-marcas` |
| Mano de Obra | `/panel/r-labor` |

> **Reubicación:** "Operaciones Renting" (`/panel/ordenes/renting`) sale a Operaciones (dominio 11).

### 6. Marketing
| Item | Ruta actual |
|---|---|
| Campañas | `/panel/marketing` |

> "Home Pública" sale de aquí (estaba mal ubicada) hacia Sitio Web (dominio 2) — el contenido
> de la home no es una campaña de marketing, es contenido del sitio.

### 7. CRM 🆕
*(vacío — no hay nada que mover; `Customer360Selector` se queda en Soporte por decisión del
usuario, no se traslada aquí)*

### 8. Ventas (agrupación de menú — `quotes` + `orders` + `payment` NO se fusionan)
| Item | Ruta actual | App backend |
|---|---|---|
| Cotizaciones | `/panel/cotizaciones` | `quotes` |
| Plantillas de Cotización | `/panel/cotizaciones/plantillas/:uuid` | `quotes` |
| Órdenes | `/panel/ordenes` | `orders` |
| Detalle de Orden | `/panel/ordenes/:uuid` | `orders` |
| Pagos | `/panel/pagos` | `payment` |

> Es el único dominio que agrupa 3 apps backend distintas bajo un mismo ítem de menú superior
> con submenús — exactamente lo que el usuario aprobó como "solo agrupación de menú".

### 9. Compras 🆕
*(vacío — dominio sin ninguna app ni ruta existente, confirmado en Fase 1)*

### 10. Inventario
*(vacío por ahora — `inventory` no tiene ninguna vista en el panel hoy; no se crea en esta
fase, ver hallazgo 4.1)*

### 11. Operaciones (consolida visualmente 5 tableros hoy dispersos en 4 módulos distintos)
| Item | Ruta actual | Origen (dominio anterior) |
|---|---|---|
| Operaciones (tickets, hub central) | `/panel/operaciones` | Ya vivía en "Logística" |
| Detalle de Operación | `/panel/operaciones/:uuid` | Ya vivía en "Logística" |
| Despachadores | `/panel/despachadores` | Ya vivía en "Logística" |
| Operaciones de Tienda (fulfillment) | `/panel/productos/operaciones` | Antes en "Tienda" |
| Operaciones de Servicios | `/panel/servicios/operaciones` | Antes en "Serv. Tecnicos" |
| Asignación de Técnicos | `/panel/servicios/asignacion-tecnicos` | Antes en "Serv. Tecnicos" (sin item de menú) |
| Operaciones Renting | `/panel/ordenes/renting` | Antes en "Renta" |

> **Este es el reflejo directo en navegación del hallazgo crítico de la Fase 1** (triple/cuádruple
> FSM duplicada). Agruparlos visualmente en el mismo dominio de menú **no resuelve** la
> duplicación de datos/lógica (eso es Fase 5), pero es un primer paso de bajo riesgo: el
> administrador empieza a *pensar* en "Operaciones" como un solo lugar, preparando el terreno
> para cuando el backend se consolide.

### 12. RRHH 🆕
*(vacío — dominio sin ninguna app ni ruta existente, confirmado en Fase 1)*

### 13. Proveedores / Contratistas 🆕 (nuevo dominio, decisión del usuario)
| Item | Ruta actual | Origen |
|---|---|---|
| Profesionales (perfiles, CV, disponibilidad) | `/panel/profesionales` | Antes en "Serv. Tecnicos" |

> Backend: `accounts` (UserProfile extendido + 9 modelos de portafolio profesional). Fase 1
> señaló que esta app mezcla auth-adyacente con portafolio profesional — Fase 2 solo reubica el
> ítem de menú; separar físicamente el backend es Fase 5.

### 14. Soporte (dominio propio, no absorbido por CRM — decisión del usuario)
| Item | Ruta actual | Nota |
|---|---|---|
| Chat de Soporte | `/panel/soporte` | **Gana item de menú por primera vez** — hoy la ruta existe pero no está enlazada desde ningún lado del sidebar (bug de navegación preexistente) |

### 15. Configuración (antes "SISTEMA")
| Item | Ruta actual | Origen |
|---|---|---|
| Usuarios | `/panel/usuarios` | Ya vivía en "Sistema" |
| Validaciones KYC | `/panel/validaciones` | Ya vivía en "Sistema" |
| Detalle de Validación | `/panel/validaciones/:uuid` | Ya vivía en "Sistema" |
| Seguridad | `/panel/seguridad` | Ya vivía en "Sistema" |
| Notificaciones | `/panel/notificaciones` | Ya vivía en "Sistema" |

> Decisión del usuario: Integraciones NO tiene entrada aquí (todo vive en Organization).
> Roles/Permisos/Auditoría/Logs/API/Webhooks (mencionados en la propuesta original) no tienen
> UI dedicada hoy — quedan como backlog de Fase 6, no se inventan ahora.

---

## 3. Tabla resumen de reubicaciones (todo lo que cambia de grupo visual)

| Ruta | Grupo actual | Grupo nuevo | Motivo |
|---|---|---|---|
| `/panel/productos/operaciones` | Tienda | **Operaciones** | Es fulfillment/logística, no catálogo |
| `/panel/servicios/operaciones` | Serv. Técnicos | **Operaciones** | Es ciclo operativo post-pago, no catálogo |
| `/panel/servicios/asignacion-tecnicos` | (huérfana) | **Operaciones** | Gana visibilidad en menú por primera vez |
| `/panel/ordenes/renting` | Renta | **Operaciones** | Es ciclo operativo post-pago, no catálogo/comercial |
| `/panel/profesionales` | Serv. Técnicos | **Proveedores/Contratistas** 🆕 | Es portafolio de personas, no catálogo de servicios |
| `/panel/home-config` | Marketing | **Sitio Web** 🆕 | Es contenido del sitio, no campaña |
| `/panel/soporte` | (huérfana, sin menú) | **Soporte** 🆕 | Gana item de menú por primera vez |
| `/panel/cotizaciones`, `/panel/ordenes`, `/panel/pagos` | 3 grupos separados (Cotizaciones, Operaciones[orders], Sistema) | **Ventas** (un solo grupo, 3 subitems) | Agrupación de menú aprobada por el usuario |
| `/panel/usuarios`, `/panel/validaciones`, `/panel/seguridad`, `/panel/notificaciones` | Sistema | **Configuración** | Renombre de sección, mismas rutas |

**Todo lo demás no listado en esta tabla se queda exactamente donde está** (Renting, Marketing-Campañas, Catálogo-resto, Servicios-resto) — la reorganización es quirúrgica, no un rediseño total.

---

## 4. Hallazgos adicionales de esta fase

### 4.1 Organization no tiene UI — riesgo de "dos fuentes visibles" temporalmente
Mientras no se construya la sección Organization (Fase 6+), el administrador seguirá editando
Marca/Contacto/Redes Sociales desde **Sitio Web → Home Pública → tabs Marca/Footer**
(`HomeConfigView.vue`), que ya escriben en `organization` por debajo (rewire hecho en la
migración anterior) pero **visualmente siguen apareciendo dentro de "Home Pública"**, lo cual
contradice conceptualmente la separación de dominios aunque técnicamente ya sea correcto. No es
un bug, es una discontinuidad de UX a resolver en Fase 6 cuando se construya el módulo
`organization` en frontend.

### 4.2 El sidebar no es dirigido por permisos ni por datos
Todo el árbol de navegación está hardcodeado en `<script setup>` de `Sidebar.vue`. Reorganizarlo
por dominios en Fase 6 implica editar ese archivo directamente (no hay capa de configuración
dinámica que abstraiga el cambio). No es un problema, pero fija el método de implementación.

### 4.3 Consistencia de nombres español/inglés
El menú actual mezcla convenciones: grupos en español ("Tienda", "Renta") pero algunos rutas y
nombres de componente en inglés. Se mantiene la convención existente en el mapa nuevo — no se
introduce un cambio de idioma no solicitado.

---

## 5. Propuesta UI/UX (sin implementar, solo criterio para Fase 6)

- Mantener el patrón visual actual (grupos colapsables con icono + color por dominio) — ya
  funciona bien y el usuario no pidió cambiarlo, solo reorganizar el contenido.
- **Organization** debería ir primero o segundo en el orden del menú (justo después de
  Dashboard) dado que es el dominio "raíz" conceptual del que dependen Sitio Web/Marketing —
  ayuda a que el admin entienda la jerarquía real.
- Los dominios vacíos (CRM, Compras, RRHH, Inventario) **no deberían aparecer en el menú
  todavía** — mostrar una sección vacía es peor UX que no mostrarla. Se agregan cuando tengan
  contenido real (Fase 5+).
- **Operaciones**, al consolidar 5 tableros de 4 apps distintas, es candidato a un ícono/color
  más prominente dado que va a crecer en importancia una vez se resuelva la Fase 1.3.1
  (duplicación de FSMs) — sugerencia, no una decisión tomada.

---

## Estado

**Fase 2: COMPLETA.** Cero cambios de código. Entregable: mapa de navegación nuevo (sección 2),
tabla de reubicaciones (sección 3), hallazgos (sección 4), criterio UI/UX (sección 5).

---

## Implementación real (2026-07-12, Fase 6)

El mapa de esta fase se implementó literalmente en
`frontend/src/components/layout/Sidebar.vue`: `moduleGroups` reescrito con los 9 grupos con
contenido real (Sitio Web, Catálogo, Servicios, Renting, Marketing, Ventas, Operaciones,
Proveedores/Contratistas, Soporte) — los 5 dominios vacíos (Organization, CRM, Compras,
Inventario, RRHH) NO se agregaron al menú, tal como recomendaba la sección 5. `systemLinks`
renombrado de "Sistema" a "Configuración" (Pagos removido, ahora vive en Ventas). **Ningún
`to` cambió de ruta** — solo se reagruparon visualmente, cero cambios en `router.js`.
`/panel/soporte` ganó su primer item de menú real (antes huérfano). `/panel/servicios/
asignacion-tecnicos` también ganó item de menú (antes huérfano).

Verificado: Vite compiló el archivo sin errores (`curl` al dev server devolvió el JS
transformado), la app carga sin errores de consola en `/panel/login` tras el cambio. **No se
verificó visualmente el sidebar ya autenticado** — requiere login con credenciales que el
clasificador de seguridad de la sesión bloqueó usar de forma automatizada (ver conversación).
Pendiente que el usuario lo confirme manualmente o autorice explícitamente una verificación
automatizada con credenciales.

**[2026-07-12, actualización] Los 3 pendientes de Fase 6 completados:**
1. `OperationBoard.vue` conectado a `effective_status` (badge de estado del tablero unificado
   de Operaciones ahora refleja el estado del satélite específico, con el fallback ya
   documentado en Fase 5 Paso 2).
2. Módulo frontend de `organization` construido desde cero: `OrganizationView.vue` (8 tabs) +
   `organization/api/views.py`/`urls.py` (8 ViewSets nuevos, API propia en
   `/api/v1/organization/`, no vía `dashboard/`) + ruta `/panel/organizacion` + primer grupo
   del sidebar. Detalle completo en
   `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`.
3. `ProfessionalsAdminList.vue` movido de `modules/accounts/` (carpeta ahora eliminada, quedó
   vacía) a `modules/proveedores/` — coincide físicamente con el dominio
   Proveedores/Contratistas. Import actualizado en `router.js`, sin otras referencias rotas
   (confirmado por grep antes de mover).

Verificado: `manage.py check` limpio, Vite compiló los 4 archivos tocados sin error, navegación
a ruta protegida sin auth redirige correctamente sin errores de consola. **No se verificó
visualmente el sidebar ya autenticado** — sigue pendiente que el usuario lo confirme
manualmente (mismo motivo que antes: credenciales no autorizadas para uso automatizado).

**⏳ Pendiente de autorización explícita para iniciar la Fase 3** (Validación de Propiedad de
Datos — matriz "Dato → Propietario → Consumidores" para TODO lo que quedó fuera del alcance de
la migración `organization` ya completada).
