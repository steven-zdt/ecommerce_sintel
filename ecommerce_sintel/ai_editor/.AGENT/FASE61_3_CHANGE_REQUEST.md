> **ADDENDUM (FASE 61.5, 2026-08-12)**: el alcance de archivos declarado aca quedo
> INCOMPLETO -- `resolve_change_context()` encontro un archivo backend adicional
> genuinamente necesario (`core/api/serializers.py::social_link_to_footer_link_shape`) y un
> test real ya existente que esta fase no habia detectado. Ver
> `FASE61_5_GRAPH_RESOLUTION.md` seccion 2 para el detalle completo y la lista de alcance
> CORREGIDA -- este documento se conserva tal cual para trazabilidad, no se reescribe.

# FASE 61.3 -- CHANGE REQUEST

**Fecha:** 2026-08-12. **Alcance:** solo documentacion, 0 archivos modificados. Verificado
contra codigo real antes de redactar (no se asumio nada sobre el estado actual del modelo,
serializer o UI).

## Verificacion previa (evita una solicitud basada en supuestos falsos)

- `organization/models.py:102-116` (`SocialLink`): campos reales hoy --
  `platform, url, icon_class, display_order, is_active` (+ `SintelBaseModel`: `uuid, created_at,
  is_deleted`). **`opens_in_new_tab` NO existe.**
- `organization/api/serializers.py:74-85` (`SocialLinkSerializer`/`SocialLinkInputSerializer`):
  confirmado que ninguno de los dos expone ni acepta ese campo.
- `frontend/src/modules/organization/OrganizationView.vue` (seccion `activeSection === 'social'`,
  lineas ~79-102): UI real hoy -- lista de links existentes (`platform`+`url`+boton eliminar) y
  un formulario inline de ALTA (3 inputs: `platform`, `url`, `icon_class` + boton "Agregar").
  **No existe UI de edicion de un link existente** (el ViewSet ya soporta `partial_update`, pero
  la vista solo usa `create`/`destroy` hoy) -- dato real relevante para no prometer "editar" algo
  que hoy no tiene UI de edicion.
- `frontend/src/components/customer/CustomerFooter.vue` (lineas 16-24, consumidor PUBLICO real
  de `socialLinks`): el `<a>` que renderiza cada link YA tiene `target="_blank"
  rel="noopener noreferrer"` **hardcodeado e incondicional** para TODOS los links, sin leer
  ningun campo del modelo. **Esto cambia el alcance real**: agregar `opens_in_new_tab` al
  modelo/API sin tocar este archivo dejaria el campo sin efecto visible (el footer seguiria
  abriendo siempre en pestana nueva, ignorando el valor nuevo) -- corregido en la seccion
  RESTRICCIONES/COMPORTAMIENTO ESPERADO abajo con este dato real, no como hipotesis.

## CHANGE_REQUEST

```
ID:          FASE61-CR-001
DOMINIO:     organization (backend) + modules/organization (frontend admin)
```

**DESCRIPCION:**
Agregar un campo booleano `opens_in_new_tab` al modelo `SocialLink`, exponerlo en la API
(`SocialLinkSerializer`/`SocialLinkInputSerializer`) y en el formulario de alta de
`OrganizationView.vue` (seccion "Redes Sociales"), para que el administrador pueda controlar,
al crear una red social, si el link debe abrirse en una pestana nueva del navegador
(`target="_blank"`) o en la misma pestana.

**OBJETIVO:**
Dar control administrativo sobre un comportamiento de navegacion que hoy esta FIJO: confirmado
que `CustomerFooter.vue` renderiza `target="_blank"` de forma incondicional para todo
`SocialLink`, sin leer ningun campo -- el objetivo real es reemplazar ese valor fijo por uno
configurable por link.

**COMPORTAMIENTO ESPERADO:**
1. `SocialLink.opens_in_new_tab`: `BooleanField(default=True)` -- por default abre en pestana
   nueva (mismo comportamiento tipico de un link externo de red social).
2. `SocialLinkSerializer` expone el campo en las respuestas GET.
3. `SocialLinkInputSerializer` acepta el campo como opcional (`required=False, default=True`) en
   el POST de creacion (`SocialLinkViewSet.create`).
4. El formulario de alta en `OrganizationView.vue` agrega un checkbox/toggle
   "Abrir en pestana nueva" (default marcado), y lo envia como parte del payload de
   `createSocialLink()`.
5. `CustomerFooter.vue` deja de hardcodear `target="_blank"` y lo reemplaza por
   `:target="link.opens_in_new_tab ? '_blank' : '_self'"` (o equivalente) -- SIN este cambio el
   campo nuevo no tendria ningun efecto observable (confirmado, no hipotetico -- ver
   verificacion previa).
6. La lista de links existentes en `OrganizationView.vue` no necesita mostrar el valor
   visualmente en esta primera iteracion (fuera de alcance -- no hay UI de edicion hoy, ver
   verificacion previa).

**RESTRICCIONES:**
- NO modificar `auth/`, `payment/`, ni ningun archivo fuera de:
  `organization/models.py`, `organization/api/serializers.py`,
  `organization/migrations/` (nueva migracion), `frontend/src/modules/organization/
  OrganizationView.vue`, `frontend/src/store/organizationAdmin.js` (si `createSocialLink()`
  necesita pasar el campo nuevo explicitamente), `frontend/src/components/customer/
  CustomerFooter.vue` (linea ~21, reemplazar el `target="_blank"` fijo -- imprescindible para
  que el campo tenga efecto real, ver COMPORTAMIENTO ESPERADO punto 5).
- NO tocar `SocialLinkViewSet.partial_update`/`destroy` (fuera del alcance del CHANGE_REQUEST).
- NO agregar UI de edicion de links existentes (no la hay hoy, no se pide crearla).
- Requiere una migracion de Django real (`makemigrations`/`migrate`) -- se evaluara en FASE 61.5
  si el ChangePlan la incluye como paso o si queda documentada como limitacion (el mecanismo de
  `ai_editor` no ejecuta migraciones automaticamente, ver `SECURITY_MODEL.md`).

**CRITERIO DE EXITO (objetivo, verificable):**
1. El campo existe en el modelo, con `default=True` y sin romper ningun `SocialLink` ya
   creado (migracion con default, no requiere backfill manual).
2. `GET api/v1/organization/social-links` devuelve `opens_in_new_tab` en cada item.
3. `POST api/v1/organization/social-links` acepta `opens_in_new_tab` opcional.
4. El formulario de alta de `OrganizationView.vue` incluye el control nuevo y lo envia.
5. `CustomerFooter.vue` respeta el valor real de `opens_in_new_tab` por link (no un
   `target="_blank"` fijo).
6. `organization/tests.py` incluye al menos un test real que verifique 2 y 3.
7. 0 tests pre-existentes rotos (los 561 del baseline FASE 61.0, descontando los 20 ya
   fallidos que son pre-existentes y no relacionados).
8. `graph Reconciliation`/`Impact Recheck` (FASE 61.17/61.19) confirman que el impacto real
   coincide con el declarado aca (backend: 1 modelo + 2 serializers + 1 migracion; frontend:
   `OrganizationView.vue` + `CustomerFooter.vue` + posiblemente `organizationAdmin.js`; sin
   archivos fuera de esa lista).

**AMBIGUEDAD:** ninguna -- a diferencia de "mejora el frontend" o "sincroniza todo" (ejemplos
explicitamente prohibidos por el prompt maestro, seccion 10), esta solicitud nombra el modelo
exacto, el campo exacto, el tipo exacto, el default exacto, los 2 archivos backend exactos y la
vista frontend exacta.
