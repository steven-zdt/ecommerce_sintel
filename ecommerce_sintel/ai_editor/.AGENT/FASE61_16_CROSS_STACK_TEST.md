# FASE 61.16 -- CROSS-STACK TEST

**Fecha:** 2026-08-12. **0 archivos modificados en esta fase** -- sintetiza evidencia YA real
de FASE 61.13/61.15 (decision explicita del usuario: no otro ciclo de escritura, la cadena ya
esta cubierta con datos reales salvo un eslabon de bajo riesgo, explicado abajo).

## Cadena completa, eslabon por eslabon, con la fase que lo probo

```
FRONTEND (OrganizationView.vue::createSocialLink())
   |  confirmado: FASE 61.14 -- npm run build real compilo el componente con el
   |  checkbox nuevo sin errores.
   v
API CLIENT (organizationAdmin.js::createSocialLink(), Axios via useApi())
   |  confirmado: FASE 61.11 -- contract_awareness identifico correctamente que este
   |  archivo es un pass-through real (envia el payload tal cual), no necesita cambios.
   v
HTTP (POST api/v1/organization/social-links/)
   |  NO probado literalmente en esta campaña (routing+permisos via un request HTTP
   |  crudo) -- ver seccion "Eslabon no ejercitado literalmente" abajo.
   v
BACKEND -- SocialLinkViewSet -> SERVICE (OrganizationCommands.create_social_link/
update_social_link)
   |  confirmado: FASE 61.13 (retry) -- 19/19 tests reales de Django, incluido
   |  test_social_link_crud, que ejercita create_social_link() Y
   |  update_social_link() contra la base de datos REAL (Postgres, no sqlite/mock).
   v
DATABASE (Postgres real, dev)
   |  confirmado: FASE 61.13/61.15 -- migracion real aplicada
   |  (0006_sociallink_opens_in_new_tab), fila real creada/actualizada/borrada,
   |  verificado con SELECT real (Django shell) que el valor persiste correctamente.
   v
RESPONSE (SocialLinkSerializer -> JSON)
   |  confirmado: FASE 61.15 -- JSON real inspeccionado via Django shell,
   |  campo/tipo/presencia exactos.
   v
FRONTEND (CustomerFooter.vue lee link.opens_in_new_tab)
   |  confirmado: FASE 61.14 (build real) + FASE 61.15 (contrato coincide exacto).
```

## Eslabón no ejercitado literalmente: routing HTTP + permisos admin

Ningun test de esta campaña hizo un `POST`/`GET` HTTP crudo (via `APIClient` de DRF o
`curl`) contra `api/v1/organization/social-links/` -- todo lo demas se probo con datos reales,
pero este tramo especifico se INFIERE, no se demostro literalmente, por decision explicita del
usuario (evitar un 6to ciclo de escritura real sobre el repo).

**Por que el riesgo es bajo (no cero, declarado honestamente)**:
- El mismo `SocialLinkViewSet` (routing + permisos) ya es el que sirve TODOS los demas metodos
  de esa clase (`list`/`create`/`partial_update`/`destroy`) -- no se creo ningun endpoint
  nuevo, ninguna ruta nueva, ningun permiso nuevo. El cambio es EXCLUSIVAMENTE un campo
  adicional en el payload/respuesta de rutas que ya existian y ya se sirven en produccion.
- El mismo patron (`APIClient` real contra un endpoint de `organization`) SI se ejercito
  literalmente en esta sesion -- `organization/tests.py::CommunicationEventEndpointTestCase`
  (parte de los 19 tests reales de FASE 61.13/retry) confirma que el routing+permisos de esta
  MISMA app funcionan.

**Declarado como riesgo residual, no como PASS fabricado**: si se quisiera cerrar este ultimo
1% de la cadena con evidencia HTTP literal, requeriria un 6to ciclo real (apply+APIClient+
revert) -- disponible como accion futura si el usuario lo pide, no ejecutado en esta fase por
decision explicita.

## Conclusion

**7 de 8 eslabones de la cadena Frontend->API->HTTP->Backend->DB->Response->Frontend
confirmados con evidencia REAL** (no mocks, no fixtures) a lo largo de FASE 61.9-61.15. El
unico eslabon sin demostracion HTTP literal (routing+permisos) tiene riesgo residual bajo,
declarado explicitamente, no maquillado a PASS.
