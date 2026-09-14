# Plan de acción — Refactorización arquitectónica de Renting

## Propósito y límites

Este plan convierte `Refactorización_Arquitectónica_Renting.md` en trabajo ejecutable. Su única meta es reducir complejidad accidental sin cambiar ningún comportamiento observable.

**Fuentes de verdad:** `ARQUITECTURA_COMPLETA_RENTIG.md` y `renting/models.py`. Cuando difieran, se debe registrar el desfase y resolverlo antes de modificar código.

**No permitido:** cambios de endpoints, URLs, payloads, permisos, migraciones históricas, reglas de negocio, precios, pagos, disponibilidad, estados, operaciones, Comodato, Renting ni flujos de usuario. No se aprueba una modificación solo por reducir líneas.

## Condición de inicio

- Crear una rama exclusiva de refactorización y fijar el commit base.
- Ejecutar y guardar el resultado de la suite actual del módulo y de los tests de integración afectados.
- Inventariar contratos públicos: rutas, serializers de entrada/salida, permisos, comandos y selectores exportados.
- Crear el directorio de evidencias `.AGENT/docs/evidencias-refactor-renting/` (no versionar datos sensibles).

**Puerta de control:** no se cambia ningún archivo de producción hasta completar las fases 0 a 2 y aprobar el informe de diagnóstico.

## Fase 0 — Línea base de compatibilidad

**Objetivo:** disponer de una referencia reproducible del comportamiento actual.

| Acción | Entregable | Criterio de salida |
|---|---|---|
| Registrar commit, migración más reciente y dependencias de Renting | `00-linea-base.md` | Entorno y versión identificables |
| Capturar rutas, métodos, permisos y esquemas de serializers | `00-contratos-api.md` | Cada endpoint tiene contrato antes/después |
| Ejecutar tests existentes y smoke tests de pago, disponibilidad y operación | reporte de ejecución | Fallos preexistentes separados de los introducidos |
| Medir métricas iniciales | `00-metricas.csv` | Conteo de modelos, LOC, serializers, commands, selectors y viewsets |

Métricas mínimas: modelos concretos/abstractos, líneas por módulo, número de endpoints, serializers, comandos, selectores, viewsets y páginas de documentación. No se interpretan como objetivo por sí solas.

## Fase 1 — Action Graph y clasificación del dominio

**Objetivo:** describir el dominio antes de decidir fusiones o extracciones.

1. Extraer de `models.py` cada modelo, relación, restricción, `related_name`, índice, señal y `property`.
2. Vincular cada modelo con sus serializers, commands, selectors, viewsets, migraciones, tests y consumidores frontend.
3. Clasificar cada modelo como **CORE**, **CONFIG**, **CATÁLOGO** o **SOPORTE**; la clasificación debe incluir justificación, propietario y riesgo de cambio.
4. Publicar `01-action-graph.md` y `01-inventario-modelos.csv`.

El grafo debe partir al menos de estos agregados: `Equipment`, `RentalRequest`, `RentalOperation`, `RentalAvailability` (`RentalPeriod` y `EquipmentBlock`), pricing y configuraciones de equipo. Debe señalar que `RentalSpecification` depende además de su grupo, y que vídeo, documento, imagen e inspección manejan recursos o reglas que pueden impedir una unificación.

**Puerta de control:** cada modelo y cada relación de `models.py` aparece una vez en el inventario; no existen nodos sin consumidor o sin decisión explícita.

## Fase 2 — Duplicación y decisiones arquitectónicas

**Objetivo:** distinguir repetición útil de complejidad accidental.

Construir `02-matriz-duplicacion.md` con una fila por grupo candidato y estas columnas:

| Candidato | Campos/reglas repetidos | Consumidores | Diferencias relevantes | Alternativas | Decisión | Métrica de mejora | Riesgo |
|---|---|---|---|---|---|---|---|

Analizar como mínimo el patrón de hijos ordenados de `Equipment`: incluidos, excluidos, características, requisitos, servicios, FAQ y especificaciones; y el patrón de configuraciones: logística, comercial y marketing.

Para cada propuesta escoger una de estas decisiones: **mantener**, **extraer base abstracta**, **unificar con discriminador**, **mover de módulo** o **retirar infraestructura de compatibilidad**. Una decisión de mantener requiere la misma evidencia que una de cambiar: por ejemplo, archivo/media, FK adicional, validaciones propias, permisos, semántica de API o ciclo de vida distinto.

**Puerta de control:** no hay modelo “candidato a eliminar” sin lista completa de referencias y estrategia de compatibilidad.

## Fase 3 — Diseño aprobado y plan de migración

**Objetivo:** diseñar cambios pequeños, reversibles y medibles.

Para cada decisión aprobada, crear una ficha en `03-decisions/` con:

- problema y evidencia de la fase 2;
- diseño actual y propuesto, con grafo antes/después;
- contratos que permanecen idénticos;
- estrategia de migración de datos, si aplica, y rollback;
- lista de imports y referencias a actualizar;
- pruebas específicas y métrica arquitectónica que debe mejorar.

Reglas de decisión:

- `EquipmentCatalogContent` solo se implementa si conserva datos, orden, activación, permisos, administración y compatibilidad. Multimedia, documentos y especificaciones agrupadas pueden quedar separados si la ficha lo justifica.
- Las propiedades de `RentalRequest` solo se eliminan después de migrar todos sus consumidores a `location_info`, `contact_info`, `costs_info` y `payment_info`, y de demostrar compatibilidad de serializers y comandos.
- Una clase abstracta solo se aprueba cuando reduce mantenimiento de una regla compartida; no debe ocultar semánticas distintas.
- `RentalCostRule` y `RentalCostAssignment` se simplifican únicamente si sus cardinalidades, consultas y reglas de asignación quedan demostrablemente equivalentes.

## Fase 4 — Extracción modular sin cambio de esquema

**Objetivo:** dividir `models.py` con riesgo mínimo.

1. Crear `renting/models/` y mover clases sin alterar sus nombres, campos, `app_label`, migraciones ni importación pública.
2. Aplicar la estructura: `common.py`, `equipment.py`, `catalog.py`, `requests.py`, `operations.py`, `pricing.py`, `marketing.py`, `commercial.py`, `availability.py`, `inspections.py`, `logistics.py` y `__init__.py`.
3. Reexportar todos los modelos desde `renting.models` para mantener los imports existentes.
4. Validar que `makemigrations --check` no propone migraciones y que las migraciones históricas siguen cargando.

**Puerta de control:** imports públicos y relaciones de Django resuelven igual; no se genera migración de esquema por el movimiento.

## Fase 5 — Simplificaciones aprobadas, de una en una

**Objetivo:** implementar solamente decisiones de la fase 3.

Orden recomendado:

1. Bases abstractas de bajo riesgo, si fueron aprobadas.
2. Eliminación de delegación interna de `RentalRequest` ya sin consumidores.
3. Consolidación de catálogo o marketing, únicamente tras una migración de compatibilidad aprobada.
4. Simplificación de reglas de costo, únicamente con pruebas de equivalencia de cálculo.

Cada cambio debe ser un commit aislado con su ficha, pruebas y resultados. Si requiere cambiar un contrato público, se rechaza o se rediseña: no se compensa con un cambio de frontend.

## Fase 6 — Adaptación de la capa de aplicación

**Objetivo:** actualizar implementación interna preservando contratos.

- Ajustar imports en services, serializers, views, admin, tareas y tests.
- Mantener commands como único punto de escritura y selectors como lectura sin efectos.
- Comparar payloads de serialización antes/después con fixtures representativas.
- Verificar explícitamente permisos de propietarios, compradores y administradores.
- Buscar y retirar código muerto solo cuando no tenga consumidores en Python, frontend, plantillas, tareas o integraciones.

## Fase 7 — Documentación concisa

**Objetivo:** dejar una arquitectura útil sin duplicar el código.

Reescribir `ARQUITECTURA_COMPLETA_RENTIG.md` para documentar agregados, responsabilidades, flujos, eventos, API pública y decisiones. Los atributos exhaustivos, getters y setters permanecen como fuente de verdad en código. Conservar una tabla de trazabilidad de los cambios aprobados y las excepciones deliberadamente no unificadas.

## Fase 8 — Verificación de equivalencia

Ejecutar, documentar y comparar contra la fase 0:

- suite del módulo, migraciones y checks de Django;
- CRUD administrativo de catálogo y configuraciones;
- creación de solicitud, disponibilidad por día/hora, bloqueo y extensión;
- cálculo de costos e impuestos;
- pago Wompi/Nequi/COD/Comodato, incluido conflicto de disponibilidad;
- ciclo de operación, inspección de retorno y notificaciones;
- endpoints, payloads, permisos, URLs, comandos y selectores públicos;
- revisión de `makemigrations --check` y de todas las migraciones existentes.

**Criterio de aceptación:** cero regresiones atribuibles a la refactorización. Cualquier diferencia de payload, estado, cálculo o permiso bloquea el cierre.

## Fase 9 — Cierre y entrega

Entregar `Informe_Final_Refactorizacion_Renting.md` con:

1. Action Graph y mapa de dependencias finales.
2. Decisiones implementadas y decisiones descartadas, con razón técnica.
3. Modelos eliminados, fusionados, renombrados o abstraídos; si no hay alguno, declararlo expresamente.
4. Código eliminado/reutilizado y comparación de métricas iniciales/finales.
5. Resultados de la matriz de compatibilidad y pruebas.
6. Riesgos residuales, rollback y trabajo futuro fuera de alcance.

El informe debe demostrar una mejora concreta de cohesión, acoplamiento, duplicación o mantenibilidad para cada cambio. Las métricas de tamaño son contexto, nunca justificación suficiente.

## Secuencia operativa resumida

`Línea base → Action Graph → Matriz de duplicación → Diseño aprobado → División de modelos → Simplificaciones aisladas → Pruebas de equivalencia → Documentación e informe final`

Ninguna flecha puede saltarse: las fases 0–3 son de diagnóstico y aprobación; las fases 4–6 son de implementación; las fases 7–9 son de verificación y cierre.
