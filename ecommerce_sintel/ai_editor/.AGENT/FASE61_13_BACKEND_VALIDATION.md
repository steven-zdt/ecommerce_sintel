# FASE 61.13 -- BACKEND VALIDATION

**Fecha:** 2026-08-12. **Confirmado explícitamente por el usuario** -- única forma real de
correr los tests de Django (el sandbox de `ai_editor` no puede, ver seccion 0). Ejecutado contra
`WORKSPACE_ROOT` real con **reversión inmediata y verificada** al finalizar.

## 0. Por qué se escribió contra el repo real

El sandbox de `ai_editor` (POST-GRAPH 7) es una copia parcial de archivos -- no tiene Django,
Postgres, ni el resto del entorno necesario para `manage.py test`. Documentado desde FASE 33 y
reconfirmado en FASE 61.8 (`tests_run_note`). Para obtener un resultado de backend REAL (no
simulado), el usuario confirmó explícitamente promover el proposal de FASE 61.9 contra
`WORKSPACE_ROOT`, correr los tests reales, y revertir todo de inmediato -- mismo mecanismo ya
probado en FASE 54-55.

## 1. Secuencia ejecutada (real)

```
1. git status de los 6 archivos objetivo: TODOS ya tenian cambios reales sin commitear
   (trabajo del usuario) -- verificado ANTES de escribir que mis rangos de linea no se
   solapaban (mismo criterio que FASE 54-55).
2. review_and_promote(..., confirm=True) -> PROMOTED. Verificado leyendo cada uno de los
   6 archivos reales: opens_in_new_tab presente en los 6.
3. docker exec ecommerce_sintel_django python manage.py makemigrations organization
   -> generó organization/migrations/0006_sociallink_opens_in_new_tab.py (herramienta REAL
   de Django, no un archivo escrito a mano).
4. docker exec ecommerce_sintel_django python manage.py migrate organization -> aplicada
   real contra la base de datos de desarrollo.
5. docker exec ecommerce_sintel_django python manage.py test organization --verbosity=2
   -> 19 tests reales corridos.
```

## 2. BACKEND_VALIDATION: **FAIL** (real, no maquillado)

```
Ran 19 tests in 2.522s
FAILED (failures=1)

FAIL: test_social_link_crud (organization.tests.OrganizationSelectorAndCommandsTests)
  File "/code/organization/tests.py", line 97, in test_social_link_crud
    self.assertFalse(link.opens_in_new_tab)
AssertionError: True is not false
```

Los otros 18 tests de `organization` (incluidos los 2 tests nuevos de `SingletonModelsTests`
del trabajo en curso del usuario, y el resto de la suite) pasaron -- el fallo es exclusivo del
test ampliado en FASE 61.9.

## 3. Causa raíz real -- GAP H: la capa de Commands nunca se toco

```python
# organization/services/commands.py (NO estaba en el alcance de FASE 61.2/61.3/61.7)
@staticmethod
@transaction.atomic
def update_social_link(link, data):
    allowed = ('platform', 'url', 'icon_class', 'display_order', 'is_active')  # <- sin opens_in_new_tab
    for field in allowed:
        if field in data:
            setattr(link, field, data[field])
    link.save()
    return link
```

`OrganizationCommands.update_social_link()` tiene un whitelist EXPLICITO de campos editables --
`opens_in_new_tab` nunca se agregó ahí, asi que `setattr()` nunca corre para ese campo. El
modelo, ambos serializers y el frontend SI tienen el campo -- pero el UNICO camino real de
escritura (`OrganizationCommands.update_social_link()`, capa de Service Layer que este proyecto
exige, ver `.AGENT.md`) lo descarta en silencio.

**Por qué se paso por alto en FASE 61.5/61.7**: `resolve_change_context()` (FASE 61.5) listó
`OrganizationCommands.create_social_link` como `backend_dependency` real, pero **NO
`OrganizationCommands.update_social_link`** -- ambos metodos son adyacentes, en la misma clase,
sobre el mismo modelo, pero el walk automatico del grafo solo encontró uno. Ni el ChangePlan
automatico (FASE 61.7) ni mi propia revision manual (que confio en la lista del grafo en vez de
leer la clase `OrganizationCommands` completa) detectaron el gap -- **se necesitó la EJECUCION
REAL del test para encontrarlo**, exactamente el valor que esta fase (61.13) esta diseñada para
aportar.

**Correccion que haria falta** (NO aplicada -- se revirtió todo, ver seccion 4): agregar
`organization/services/commands.py::OrganizationCommands.update_social_link()` al alcance
declarado, con `'opens_in_new_tab'` sumado al tuple `allowed`.

## 4. Reversión -- verificada completa

```
1. docker exec ecommerce_sintel_django python manage.py migrate organization 0005
   -> Unapplying organization.0006_sociallink_opens_in_new_tab... OK
2. rm organization/migrations/0006_sociallink_opens_in_new_tab.py
3. rollback_outcome(WORKSPACE_ROOT, outcome) -> status: ROLLED_BACK,
   files_restored: los 6 archivos.
4. Verificacion SHA-256 completo (antes vs despues del rollback): LOS 6 ARCHIVOS COINCIDEN
   EXACTOS, byte a byte.
5. git status: identico al estado ANTES de esta fase (mismas 6 rutas "M" pre-existentes,
   ninguna nueva).
6. grep -r "opens_in_new_tab" sobre los 6 archivos: 0 coincidencias.
7. organization/migrations/: identico al estado anterior (hasta 0005, sin 0006).
```

**El repositorio quedo exactamente como estaba, incluida la base de datos de desarrollo
(migracion revertida antes de borrar el archivo).**

## 5. RETRY -- GAP H corregido, PASS genuino (confirmado por el usuario)

Corregido `organization/services/commands.py::OrganizationCommands.update_social_link()`
agregando `'opens_in_new_tab'` al tuple `allowed` -- **unico cambio nuevo respecto al intento 1**
(los otros 6 archivos, identicos). Proposal ampliado a **7 operaciones/7 archivos**. Misma
secuencia completa: promote real (`confirm=True`) -> `makemigrations` real (regenero
`0006_sociallink_opens_in_new_tab.py`, mismo contenido) -> `migrate` real -> **`manage.py test
organization` real**.

```
Ran 19 tests in 2.500s

OK
```

**19/19 tests PASS, incluido `test_social_link_crud` (el ampliado en FASE 61.9).**
`BACKEND_VALIDATION = PASS` para el caso completo, con la correccion aplicada.

**Reversion del retry -- verificada completa, igual rigor que el intento 1:**
```
1. migrate organization 0005 -> Unapplying organization.0006... OK
2. rm organization/migrations/0006_sociallink_opens_in_new_tab.py
3. rollback_outcome() -> ROLLED_BACK, 7 archivos restaurados
4. SHA-256 completo (7 archivos): TODOS COINCIDEN EXACTOS
5. git status: identico al estado previo (mismas rutas "M" pre-existentes)
6. grep "opens_in_new_tab": 0 coincidencias
7. organization/migrations/: identico (hasta 0005, sin 0006)
```

## Conclusion

**Primer intento: BACKEND_VALIDATION = FAIL** (GAP H real, capa de Commands con whitelist
explicito no actualizado -- ni el grafo ni la revision manual lo detectaron, solo la ejecucion
real del test). **Segundo intento (retry, GAP H corregido): BACKEND_VALIDATION = PASS, 19/19
tests reales.** Ambas escrituras contra `WORKSPACE_ROOT` revertidas y verificadas al 100%
(SHA-256 exacto, git status identico, 0 rastros).

Esto es exactamente el resultado que FASE 61 esta diseñada para producir: un cambio cross-stack
de apariencia trivial (1 campo booleano) requeria tocar **7 archivos reales, no 6** -- el
septimo capa (Service Layer/Commands, la que este mismo proyecto exige como unico camino de
escritura, ver `.AGENT.md`) no fue detectada ni por el grafo (que listo `create_social_link`
pero no el metodo adyacente `update_social_link`, misma clase, mismo modelo) ni por la revision
manual (que confio en la lista del grafo) -- **solo la ejecucion real del test lo encontro**, y
solo una segunda iteracion con correccion real lo resolvio. Prueba directa del valor de FASE
61.13 sobre confiar unicamente en validaciones esteticas (sintaxis, contratos, arquitectura), y
del valor de FASE 61.25 "Retry Controlado" -- este caso tomo 2 intentos reales, no 1.
