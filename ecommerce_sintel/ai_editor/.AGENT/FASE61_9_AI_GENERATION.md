# FASE 61.9 -- AI GENERATION

**Fecha:** 2026-08-12. **0 archivos del repo real modificados** -- todo aplicado y verificado
UNICAMENTE en sandbox (`repository.create_sandbox()`), limpiado al final (`sandbox.cleanup()`).

## 0. Cambio de premisa (regla explicita del usuario, 2026-08-12)

Esta fase originalmente pedia invocar al LLM real (Ollama) para que PROPUSIERA el patch. Por
instruccion explicita del usuario, esa premisa se descarta: **Ollama nunca decide ediciones de
codigo de este proyecto** (reservado solo para el chatbot de soporte, `ai_engine`). El
`PatchProposal` de esta fase fue **redactado por Claude (esta sesion)**, no generado por un LLM
llamado en vivo -- documentado como tal, sin fingir que vino de Ollama.

```
MODEL:    Claude (Claude Code, esta sesion) -- NO Ollama/llama3.1:8b
PROVIDER: N/A (no hubo llamada a ai_editor.llm.complete())
VERSION:  N/A
TEMPERATURE / MAX TOKENS / STRUCTURED OUTPUT CONFIG: N/A -- el PatchProposal se construyo
          directo como objetos Python reales (ai_editor.generation.models.PatchProposal/
          PatchOperation), no via parseo de una respuesta de texto libre.
```

## 1. PatchProposal construido (real, aplicado despues contra sandbox real)

```
proposal_id: fase61-9-social-link-opens-in-new-tab
operations: 7
archivos tocados: core/api/serializers.py, frontend/src/components/customer/CustomerFooter.vue,
                   frontend/src/modules/organization/OrganizationView.vue,
                   organization/api/serializers.py, organization/models.py, organization/tests.py
confidence: 0.9 (auto-declarada, no auto-reportada por un LLM esta vez)
```

**Contenido real de cada operacion** (resumen -- old_content/new_content completos son texto
real leido/escrito, no fabricado):

1. `organization/models.py::SocialLink` -- agrega `opens_in_new_tab = models.BooleanField
   (default=True)` despues de `is_active`.
2. `organization/api/serializers.py::SocialLinkSerializer` -- agrega `'opens_in_new_tab'` a
   `fields`.
3. `organization/api/serializers.py::SocialLinkInputSerializer` -- agrega
   `opens_in_new_tab = serializers.BooleanField(required=False, default=True)`.
4. `core/api/serializers.py::social_link_to_footer_link_shape` -- agrega
   `'opens_in_new_tab': link.opens_in_new_tab` al dict de retorno (**GAP F**, FASE 61.5/61.6).
5. `frontend/.../OrganizationView.vue` -- **una sola operacion atomica** (ver hallazgo abajo)
   que agrega el checkbox al form de alta, el default `true` en `newSocialLink` ref, y el mismo
   default en el reset post-alta.
6. `frontend/.../CustomerFooter.vue` -- reemplaza `target="_blank"` fijo por
   `:target="link.opens_in_new_tab === false ? '_self' : '_blank'"` (**GAP F**). `=== false`
   (no negacion simple) para que datos sin el campo sigan abriendo en pestana nueva (mismo
   comportamiento de hoy, decision explicita documentada en `assumptions`).
7. `organization/tests.py::test_social_link_crud` -- amplia el test real existente: verifica
   default `True` al crear, y que `update_social_link()` puede ponerlo en `False`.

```
risks declarados:
  - Requiere una migracion Django real (makemigrations+migrate) que este mecanismo no genera
    ni ejecuta -- limitacion documentada, no aplicada en sandbox.
  - organizationAdmin.js::createSocialLink() se dejo SIN modificar -- confirmado pass-through
    real (envia el payload tal cual), no necesita cambios.
assumptions declaradas:
  - default True preserva el comportamiento actual para SocialLink ya creados.
  - CustomerFooter.vue usa comparacion estricta '=== false', no negacion simple.
tests_to_update: ['organization/tests.py::OrganizationSelectorAndCommandsTests.test_social_link_crud']
```

## 2. HALLAZGO REAL del propio mecanismo -- 3 operaciones separadas sobre el mismo archivo
rompen el fingerprint

Primer intento: 3 `PatchOperation` distintas sobre `OrganizationView.vue` (template, lineas
78-104; `newSocialLink` ref, linea 218; `createSocialLink()`, lineas 278-290) -- las primeras 2
se aplicaron OK, la tercera fallo:

```
FINGERPRINT_MISMATCH: El contenido real de 'OrganizationView.vue' lineas 218-218 no coincide
con el fingerprint esperado -- el archivo cambio desde que se genero el plan.
```

**Causa real**: la primera operacion (template) inserto 4 lineas nuevas ANTES de la linea 218
dentro del SANDBOX -- desplazando el `newSocialLink` real a la linea 222. La segunda operacion
seguia usando el numero de linea ESTATICO (218) calculado ANTES de aplicar la primera, y el
Patch Engine (POST-GRAPH 6, por diseno) verifica fingerprint por RANGO DE LINEAS -- correctamente
detecto la discrepancia y **rechazo aplicar en vez de escribir sobre contenido equivocado**
(el guardrail funciono exactamente como deberia). **Correccion**: se fusionaron las 3
operaciones en UNA sola que cubre el rango completo (78-290), aplicada atomicamente.

**Leccion real para cualquier generador (LLM o humano)**: multiples operaciones sobre el MISMO
archivo en rangos de lineas no contiguos son inherentemente fragiles si una operacion anterior
cambia el NUMERO DE LINEAS del archivo -- deben fusionarse en una sola operacion que cubra todo
el tramo afectado, o el Patch Engine las rechazara (correctamente) en la segunda. Este es un
hallazgo real sobre el DISEÑO del mecanismo (POST-GRAPH 6), no un bug -- el fingerprint hizo
exactamente su trabajo.

## 3. Resultado tras la correccion -- aplicado y validado real

```
run_sandbox_validation_loop(): ready_for_approval = True
apply_result.applied: True (7/7 operaciones APPLIED, 0 fallidas)
validation_report.level_1_passed: True
  organization/models.py: sintaxis Python valida
  organization/api/serializers.py: sintaxis Python valida
  core/api/serializers.py: sintaxis Python valida
  organization/tests.py: sintaxis Python valida
  OrganizationView.vue: sintaxis JS valida (node --check)
  CustomerFooter.vue: sintaxis JS valida (node --check)
```

## 4. Metricas reales (adelanto de FASE 61.10)

```
JSON valido: N/A (no aplica -- construccion directa, no parseo de texto libre)
schema valido: SI (PatchProposal/PatchOperation reales, sin campos faltantes)
operaciones: 7
archivos: 6
simbolos declarados: 6 (2 operaciones de organization/api/serializers.py comparten archivo)
caracteres old_content (total): 14,005
caracteres new_content (total): 14,703
caracteres netos agregados: 698
retries: 1 (el intento con 3 operaciones separadas -- corregido a 1 operacion fusionada, no
           por un error de FORMA sino de DISEÑO del patch; ver seccion 2)
errores: 0 (tras la correccion)
warnings: 0
```

## Conclusion

Un patch cross-stack real (6 archivos, backend Django + frontend Vue) se construyo, se aplico
sobre un sandbox real, y paso validacion de sintaxis Nivel 1 -- con autoria de Claude, no de
Ollama, por la regla explicita del usuario. Se encontro y documento un hallazgo real y honesto
sobre el propio Patch Engine (fragilidad de multiples operaciones no fusionadas en el mismo
archivo) -- no un defecto del mecanismo (el guardrail funciono), sino una leccion sobre como
CONSTRUIR proposals correctamente, aplicable tanto a un LLM como a un generador humano.
