# FASE 61.15 -- CONTRACT VALIDATION

**Fecha:** 2026-08-12. **Confirmado explícitamente por el usuario** -- mismo criterio que
FASE 61.13/61.14. Ejecutado contra `WORKSPACE_ROOT` real con **reversión inmediata y
verificada**, incluida limpieza de datos reales en la base de datos de desarrollo.

## Secuencia ejecutada

```
1. review_and_promote(confirm=True) sobre los 5 archivos backend (mismos de FASE 61.13,
   ya probados) -> PROMOTED.
2. makemigrations + migrate reales (misma migracion regenerada).
3. Django shell real: SocialLink.objects.create(...) -> SocialLinkSerializer(link).data
   y social_link_to_footer_link_shape(link) -- el JSON REAL que devolverian los 2
   endpoints, no un mock.
4. link.delete() -- limpieza del registro de prueba (verificado despues: id=9 ya no
   existe, 0 registros huerfanos).
```

## Comparación BACKEND RESPONSE vs FRONTEND EXPECTATION

**Endpoint 1 -- `api/v1/organization/social-links/` (`SocialLinkSerializer`, admin):**
```json
{
  "id": 9, "uuid": "500f6b6c-...", "platform": "Instagram",
  "url": "https://instagram.com/sintel", "icon_class": "",
  "display_order": 0, "is_active": true,
  "opens_in_new_tab": true,
  "created_at": "2026-08-12T13:08:44.764549-05:00"
}
```

**Endpoint 2 -- `core/footer/` (`social_link_to_footer_link_shape`, público -- el que
consume `CustomerFooter.vue`):**
```json
{
  "id": 9, "uuid": "500f6b6c-...", "title": "Instagram",
  "url": "https://instagram.com/sintel", "category": "social", "group_name": "",
  "icon_class": "", "display_order": 0, "is_active": true,
  "opens_in_new_tab": true,
  "created_at": "2026-08-12 18:08:44.764549+00:00"
}
```

| Aspecto | Backend REAL | Frontend ESPERA | Match |
|---|---|---|---|
| Nombre del campo | `opens_in_new_tab` | `link.opens_in_new_tab` (`CustomerFooter.vue`), `newSocialLink.opens_in_new_tab` (`OrganizationView.vue`) | SI, exacto |
| Tipo | `bool` JSON nativo (`true`/`false`) | Comparacion `=== false` (espera booleano real, no string `"false"`) | SI |
| Presencia | Siempre presente (default del modelo, nunca `null`/ausente) | `link.opens_in_new_tab === false ? '_self' : '_blank'` -- si faltara, cae a `'_blank'` (mismo comportamiento actual, backward-compatible por diseño) | SI, con fallback seguro |
| HTTP method/URL | Sin cambios (`GET`/`POST` ya existentes) | Sin cambios en el frontend | SI |
| Pagination/errors | Sin cambios (el campo no afecta paginacion ni manejo de errores) | N/A | SI |

**0 CONTRACT_MISMATCH.**

## Reversión -- verificada completa (incluye datos, no solo código)

```
1. migrate organization 0005 -> Unapplying organization.0006... OK
2. rm organization/migrations/0006_sociallink_opens_in_new_tab.py
3. rollback_outcome() -> ROLLED_BACK, 4 archivos restaurados
4. SHA-256 completo (4 archivos): TODOS COINCIDEN EXACTOS
5. git status: identico al estado previo
6. grep "opens_in_new_tab": 0 coincidencias
7. Datos: el SocialLink de prueba (id=9) fue borrado explicitamente dentro del propio
   script de verificacion -- confirmado id=9 ya no existe, 0 registros huerfanos. El
   registro "Instagram" que SI queda en la base (id=2, url .../sintel.technology,
   creado 2026-07-12) es un dato REAL preexistente del usuario, no relacionado.
```

## Conclusion

**CONTRACT VALIDATION: PASS, 0 mismatch.** El backend expone exactamente el campo, tipo y
nombre que el frontend espera consumir, en ambos endpoints relevantes (admin y público).
Reversión completa verificada, incluida la limpieza del dato de prueba creado durante la
inspección.
