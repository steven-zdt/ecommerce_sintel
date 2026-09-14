# AI_MODEL_BENCHMARK -- FASE 61.24 Clasificación / FASE 61.26-28 Casos adicionales / FASE 61.29 Decisión

**Fecha:** 2026-08-12.

## FASE 61.24 -- Clasificación (LEVEL 0-7, con evidencia, nunca sin ella)

**Regla del prompt maestro aplicada literal: "NO asignar un nivel sin evidencia."** Dado que
esta campaña midió 2 cosas distintas (ver `AI_MODEL_QUALIFICATION_REPORT.md`), se clasifican
por separado -- fusionarlas produciría un nivel que ninguna de las dos partes sostiene por sí
sola.

### Ollama (`llama3.1:8b`) -- capacidad real, medida en 2 tareas distintas

```
Change Intent (FASE 61.4, interpretar lenguaje natural -> JSON de 6 campos):
  LEVEL 2 -- produce output estructurado CORRECTO (0 entidades alucinadas, dominio
  correcto, verificado independientemente contra el grafo real).

Patch Generation (FASE 51-53, generar un PatchProposal completo):
  LEVEL 0 -- no produjo JSON valido en 2 intentos reales (`INVALID_JSON`, rechazado sin
  reparar, por diseño).
```

**Conclusión sobre Ollama**: capaz en tareas de EXTRACCIÓN/CLASIFICACIÓN de complejidad baja
(intent parsing), no capaz (en este entorno, con este modelo de 8B) de GENERACIÓN de patches
estructurados multi-campo. No se prueba con un caso más simple de generación en esta campaña
-- posible trabajo futuro, no fabricado aquí.

### Mecanismo `ai_editor` + Claude como autor (FASE 61.9-61.22, este mismo caso)

```
LEVEL 7 -- cambio cross-stack real (backend + API + frontend) CON tests reales (19/19,
tras 1 retry genuino) Y reconciliación de grafo consistente (0 unexpected impact) Y
0 drift de impacto.
```

**Aclaración obligatoria (no se puede omitir sin fabricar una conclusión falsa)**: este LEVEL 7
mide la **solidez del MECANISMO** (validación por capas, sandbox, reconciliación, guardrails de
seguridad, capacidad de revertir con exactitud verificada) cuando el CONTENIDO del patch lo
decide un agente con criterio (Claude, bajo confirmación humana explícita en cada escritura
real) -- **no es una medición de autonomía de IA sin supervisión.** Ningún paso de esta campaña
escribió sobre el repo real sin confirmación humana previa, y cada escritura real fue revertida
y verificada antes de continuar.

## FASE 61.25 -- Retry Controlado (ya ocurrió, real, no simulado)

```
ATTEMPT 1: FAIL -- GAP H (organization/services/commands.py::update_social_link, whitelist
           sin el campo nuevo). Correccion: agregar 'opens_in_new_tab' al tuple allowed.
ATTEMPT 2: PASS -- 19/19 tests reales.
```

1 de 3 intentos permitidos usado -- dentro del límite, con causa/corrección documentadas por
completo (ver `FASE61_13_BACKEND_VALIDATION.md`).

## FASE 61.26-28 -- Segundo/Tercer caso

**No ejecutados en esta campaña** -- el prompt maestro (sección 33) exige `PASS` o
`PASS WITH MINOR WARNING` en el primer caso para habilitar un segundo. El primer caso tuvo un
`FAIL` real en su primer intento (corregido en el retry) -- criterio conservador: no se
interpreta el `PASS` del retry como automáticamente habilitante para escalar a un caso más
difícil sin que el usuario lo decida explícitamente. Queda como acción disponible, no ejecutada.

## FASE 61.29 -- Decisión

Según la sección 36 del prompt maestro:

```
A. MODELO SUFICIENTE (para continuar a Model Router)         -- NO aplica a Ollama solo
   (LEVEL 0 en generacion de patches, ver arriba).
B. MODELO SUFICIENTE PARA CAMBIOS SIMPLES                     -- SI aplica a Ollama, acotado
   a tareas de clasificacion/extraccion (Change Intent), no generacion de codigo.
C. MODELO INSUFICIENTE (no continuar hacia autonomia)         -- SI aplica a Ollama para
   generacion de patches -- no continuar hacia FASE 62 "Model Router" con Ollama como
   generador autonomo de codigo sin que un humano/Claude redacte el contenido.
D. GRAPH GAP                                                    -- SI, 6 gaps reales (A-F, H)
   -- ninguno culpa al modelo por fallar donde el grafo no tenia informacion suficiente.
E. FRONTEND ARCHITECTURE GAP                                    -- parcialmente (GAP C, 25
   componentes sin diagnosticar) -- no bloqueante para este caso.
```

**Decisión combinada, honesta**: el MECANISMO (`ai_editor`) es sólido -- LEVEL 7 demostrado con
evidencia real de punta a punta, guardrails de seguridad funcionando exactamente como se
diseñaron (bloqueo correcto del `FINGERPRINT_MISMATCH` en FASE 61.9, reversión exacta
verificada 4 veces). **Ollama (`llama3.1:8b`) NO califica todavía para generación autónoma de
patches** -- sí califica para tareas de intención/clasificación. La regla explícita del
usuario (Ollama nunca decide ediciones de código) queda, con esta evidencia, no solo como
política sino como **decisión técnicamente justificada** por el propio comportamiento medido
del modelo.

## Tabla benchmark (1 caso ejecutado)

| Caso | Intent | Graph | Plan | Patch | Backend | Frontend | Contract | Architecture | Tests | Reconciliation |
|------|--------|-------|------|-------|---------|----------|----------|---------------|-------|-----------------|
| 1 (SocialLink.opens_in_new_tab) | PASS | PASS | PASS | PASS | PASS (retry 1) | PASS | PASS | PASS | PASS | PASS |
