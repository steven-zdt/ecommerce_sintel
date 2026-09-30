# PLAN DE IMPLEMENTACIÓN — OPTIMIZACIÓN CRUD COMPLETO DEL MÓDULO SERVICIOS

**Proyecto:** Sintel ERP / Ecommerce Multitenant  
**Módulo objetivo:** `technical_services` / Servicios  
**Tipo:** Plan técnico de implementación para IA editora  
**Fecha:** 2026-09-30  
**Objetivo principal:** simplificar, optimizar y hacer eficiente el CRUD completo de Servicios sin alterar la lógica de negocio existente.

---

## 1. OBJETIVO

Optimizar el módulo completo de **Servicios** eliminando:

- código muerto;
- lógica duplicada;
- consultas ORM innecesarias;
- cálculos repetidos;
- serializers sobrecargados;
- endpoints redundantes;
- componentes frontend duplicados;
- stores o llamadas API repetidas;
- formularios y flujos innecesariamente complejos;
- lógica de CRUD mezclada con procesos operativos.

### Restricción principal

**NO eliminar ni modificar la lógica de negocio que actualmente sea necesaria.**

La optimización debe reducir complejidad técnica y costo de ejecución, pero conservar:

- catálogo de servicios;
- categorías;
- niveles;
- variantes;
- materiales;
- configuraciones;
- precios;
- reglas de costos;
- cotización;
- checkout;
- confirmación/reversión de disponibilidad;
- solicitudes;
- operaciones;
- planificación;
- asignación de técnicos;
- estados operativos;
- incidentes;
- notificaciones;
- integración de pago;
- trazabilidad.

La regla será:

> **Eliminar complejidad accidental, no complejidad de negocio.**

---

# 2. FUENTE BASE

La implementación debe partir de la documentación:

`IMPLEMENTATION_SUMMARY(20260930-143846).md`

La documentación identifica específicamente:

- arquitectura del módulo `technical_services`;
- endpoints;
- Commands y Selectors;
- sistema de precios;
- checkout;
- `ServiceOperation`;
- asignación de técnicos;
- fachada administrativa;
- sistemas legacy;
- optimizaciones N+1 existentes;
- cálculo de precios duplicado.

No asumir que todo lo descrito en la documentación sigue existiendo exactamente igual.

**Antes de modificar código, inspeccionar el código real del repositorio.**

---

# 3. PRINCIPIO ARQUITECTÓNICO

Mantener el patrón existente:

```text
Frontend
   ↓
API / ViewSet
   ↓
Commands / Selectors
   ↓
Models
   ↓
PostgreSQL
```

### Commands

Responsables de escrituras:

- create;
- update;
- soft delete;
- activate/deactivate;
- operaciones de negocio.

### Selectors

Responsables exclusivamente de lecturas:

- list;
- detail;
- filtros;
- estadísticas;
- consultas optimizadas.

### Views / ViewSets

Deben actuar como capa HTTP.

Evitar:

```python
Model.objects.filter(...)
```

directamente en Views cuando la arquitectura ya dispone de Selectors.

Evitar lógica de negocio dentro de serializers o views si puede residir correctamente en Commands/Selectors.

---

# 4. SEPARACIÓN FUNDAMENTAL

El problema principal a resolver es la saturación del módulo Servicios.

Separar conceptualmente:

## A. CRUD DE CATÁLOGO

Debe encargarse de:

- Servicios;
- Categorías;
- Niveles;
- Variantes;
- Materiales;
- Configuración;
- información comercial;
- precios y características necesarias.

## B. COTIZACIÓN / PRICING

Debe encargarse de:

- cálculo de precio;
- costos;
- impuestos;
- descuentos;
- duración;
- reglas dinámicas;
- historial de precios.

## C. OPERACIÓN

Debe encargarse de:

- solicitudes;
- ServiceOperation;
- planificación;
- disponibilidad;
- asignación;
- técnicos;
- estados;
- incidentes;
- notificaciones.

### IMPORTANTE

No crear nuevas aplicaciones Django únicamente para realizar esta separación.

Primero organizar responsabilidades dentro de la arquitectura existente.

---

# 5. CRUD OBJETIVO

El CRUD administrativo de Servicios debe poder realizar de forma clara:

```text
LISTAR
BUSCAR
FILTRAR
VER DETALLE
CREAR
EDITAR
ACTIVAR
DESACTIVAR
SOFT DELETE
RESTAURAR (si el modelo/negocio actual lo soporta)
```

El CRUD de catálogo **NO debe ejecutar innecesariamente**:

- checkout;
- Wompi;
- planificación;
- asignación de técnicos;
- FSM de ServiceOperation;
- incidentes;
- notificaciones;
- operaciones de despacho.

Estas funciones solamente deben ejecutarse cuando el flujo de negocio correspondiente las requiera.

---

# 6. AUDITORÍA BACKEND OBLIGATORIA

Antes de eliminar código, realizar inventario completo de:

```text
technical_services/
├── api/
├── services/
├── serializers/
├── selectors/
├── commands/
├── models/
├── signals/
├── filters/
├── permissions/
└── tests/
```

Si la estructura real difiere, adaptarse a ella.

Para cada archivo determinar:

| Elemento | Acción |
|---|---|
| Función usada | CONSERVAR |
| Función duplicada | CONSOLIDAR |
| Función sin referencias | INVESTIGAR |
| Endpoint sin consumidores | INVESTIGAR |
| Serializer duplicado | CONSOLIDAR |
| Query repetida | OPTIMIZAR |
| Código legacy | MARCAR |
| Código crítico de negocio | NO ELIMINAR |
| Import no utilizado | ELIMINAR |

---

# 7. BÚSQUEDA DE CÓDIGO MUERTO

Buscar referencias reales antes de eliminar:

- funciones;
- clases;
- métodos;
- serializers;
- endpoints;
- rutas;
- stores;
- composables;
- componentes;
- imports;
- constantes;
- tipos;
- interfaces;
- helpers;
- servicios API.

No eliminar algo solamente porque parece innecesario.

Para cada candidato:

```text
1. localizar definición
2. buscar referencias globales
3. verificar rutas
4. verificar frontend
5. verificar tests
6. verificar integraciones
7. verificar documentación
8. eliminar solamente si no tiene dependencia funcional
```

Registrar cada eliminación.

---

# 8. BÚSQUEDA DE DUPLICACIÓN

Buscar específicamente:

## Backend

- cálculos de precio repetidos;
- validaciones repetidas;
- filtros repetidos;
- consultas ORM repetidas;
- serialización repetida;
- métodos con responsabilidad equivalente;
- Commands duplicados;
- Selectors duplicados.

## Frontend

- llamadas API repetidas;
- métodos CRUD duplicados;
- formularios equivalentes;
- modales equivalentes;
- lógica de carga repetida;
- transformaciones de datos repetidas;
- stores que mantienen el mismo estado;
- componentes legacy.

---

# 9. OPTIMIZACIÓN CRÍTICA DEL PRECIO

La documentación identifica un problema concreto:

`ServiceVariantSerializer.get_calculated_price()`

y

`ServiceVariantSerializer.get_price_info()`

pueden ejecutar separadamente:

```python
ServiceSelector.get_variant_quotation(obj)
```

Esto puede producir el mismo cálculo más de una vez por variante.

## IMPLEMENTAR

Calcular la cotización una sola vez por instancia durante la serialización.

Conceptualmente:

```python
quotation = self._get_cached_quotation(obj)
```

y reutilizar:

```python
quotation["calculated_price"]
quotation["price_info"]
```

### RESTRICCIÓN

No modificar las reglas de negocio del cálculo.

No cambiar:

- SETUP;
- OPERATIONAL;
- TAX;
- DISCOUNT;
- PERCENTAGE;
- FLAT;
- asignaciones globales;
- asignaciones por variante;
- descuentos;
- duración.

Solo evitar ejecutar el mismo cálculo repetidamente.

---

# 10. OPTIMIZACIÓN DE QUERIES

La documentación indica optimizaciones N+1 ya realizadas.

Conservarlas y verificar que sigan funcionando.

Especialmente:

```text
variants
variants__materials
variants__materials__product_variant__product
```

No introducir consultas que rompan el prefetch cache.

Evitar patrones como:

```python
obj.variants.filter(...)
```

cuando ya existe un `prefetch_related()` adecuado y pueda utilizarse:

```python
obj.variants.all()
```

seguido de filtrado en memoria cuando sea apropiado.

---

# 11. MÉTRICAS OBLIGATORIAS

Antes y después de la optimización medir:

### Backend

- cantidad de queries;
- tiempo total;
- tiempo SQL;
- cantidad de objetos serializados;
- tamaño aproximado del payload.

### Endpoints mínimos

```text
GET /api/v1/services/services/
GET /api/v1/services/services/{uuid}/
POST /api/v1/services/services/
PATCH /api/v1/services/services/{uuid}/
DELETE /api/v1/services/services/{uuid}/
```

Y los endpoints equivalentes de:

- categorías;
- niveles;
- variantes;
- materiales;
- configuración.

### Objetivo

No establecer una cifra arbitraria antes de medir.

Primero crear baseline.

Después demostrar mejora.

---

# 12. OPTIMIZACIÓN DEL SELECTOR DE LISTADO

Revisar:

```text
ServiceSelector.list_all_for_admin()
```

Verificar:

- `select_related`;
- `prefetch_related`;
- columnas innecesarias;
- ordenamiento;
- filtros;
- paginación;
- serialización;
- conteos;
- agregaciones.

No traer información pesada si la tabla de listado no la necesita.

### Principio

La vista de LISTADO no debe cargar todo el detalle del servicio.

---

# 13. LISTADO VS DETALLE

Separar las necesidades de datos.

## LISTADO

Mostrar solamente lo necesario:

```text
uuid
nombre
categoría
estado
precio base/resumen
cantidad de variantes
fecha
acciones
```

## DETALLE

Cargar:

```text
información completa
variantes
materiales
precios
configuración
reglas aplicables
historial cuando corresponda
```

Evitar serializar relaciones profundas en cada fila del listado.

---

# 14. SERIALIZERS

Auditar todos los serializers del módulo.

Buscar:

- `SerializerMethodField` costosos;
- consultas ORM dentro de métodos;
- cálculos repetidos;
- propiedades que disparan queries;
- datos no utilizados por frontend;
- serializers diferentes que representan la misma entidad.

Crear una representación adecuada para:

```text
ServiceListSerializer
ServiceDetailSerializer
ServiceWriteSerializer
```

solo si el código actual lo justifica.

No crear serializers nuevos innecesariamente.

---

# 15. WRITE SERIALIZER

El serializer de escritura debe validar datos.

No debe convertirse en un segundo Command.

Evitar:

```python
def create(...):
    # lógica compleja de negocio
```

si la arquitectura ya tiene Commands.

Preferir:

```text
HTTP
 ↓
Serializer validation
 ↓
Command
 ↓
Model
```

---

# 16. FRONTEND — CRUD

Auditar el frontend del módulo.

Identificar componentes equivalentes a:

```text
ServiceList
ServiceForm
ServiceDetail
ServiceModal
ServiceDrawer
ServiceTable
ServiceStore
ServiceApi
```

No mantener dos implementaciones para el mismo CRUD.

### Objetivo

Tener una única ruta funcional para:

```text
listar → crear → editar → detalle → activar/desactivar → eliminar
```

---

# 17. FRONTEND — API

Centralizar las llamadas CRUD.

Evitar:

```javascript
fetch(...)
axios(...)
apiClient(...)
serviceApi(...)
```

para la misma operación en distintos lugares.

Usar el cliente API existente del proyecto.

Mantener:

```text
list()
get()
create()
update()
remove()
activate()
deactivate()
```

solo si esas operaciones existen realmente.

---

# 18. FRONTEND — ESTADO

Revisar si existen múltiples fuentes de estado para Servicios.

Evitar que:

```text
ServiceStore
+
Componente
+
Modal
```

mantengan copias independientes del mismo objeto.

Preferir una única fuente de estado para el CRUD.

---

# 19. OPERACIONES — NO ROMPER

No eliminar ni simplificar incorrectamente:

`ServiceOperation`.

Debe conservarse su responsabilidad operacional.

Mantener:

- estados;
- planificación;
- disponibilidad;
- asignación;
- incidentes;
- cierre;
- cancelación;
- notificaciones;
- dashboard;
- reglas de despacho.

El CRUD de catálogo no debe absorber estas responsabilidades.

---

# 20. ASIGNACIÓN DE TÉCNICOS

La documentación identifica dos sistemas:

```text
ServiceOperation.technician
OrderServiceDetail.technician
```

La fuente actual de verdad para escritura operacional es:

```text
ServiceOperation.technician
```

No eliminar inmediatamente el campo legacy.

## FASE INICIAL

Auditar todas las escrituras sobre:

```text
OrderServiceDetail.technician
```

Identificar:

- quién escribe;
- quién lee;
- qué panel lo utiliza;
- qué endpoints dependen de él.

## FASE POSTERIOR

Cuando las dependencias estén confirmadas:

1. bloquear nuevas escrituras legacy;
2. migrar consumidores;
3. mantener lectura temporal;
4. implementar auditoría de divergencia;
5. eliminar cuando no existan consumidores.

---

# 21. FACHADA ADMINISTRATIVA

Conservar:

```text
ServiceAdminRequestSelector
ServiceAdminRequestOrchestrator
```

si el código real confirma que siguen siendo utilizados.

Su responsabilidad debe continuar siendo:

```text
Order
+
ServiceOperation
=
vista administrativa consolidada
```

No duplicar dentro de la fachada la lógica de Commands/Selectors existentes.

La fachada debe orquestar, no convertirse en una nueva capa de negocio duplicada.

---

# 22. COTIZACIÓN

Mantener:

```text
/api/v1/services/services/{uuid}/quotation/
```

cuando el flujo real lo requiera.

Debe continuar soportando:

- variant_uuid;
- duration;
- discount_pct;
- reglas dinámicas.

Pero evitar que el endpoint de CRUD normal ejecute automáticamente una cotización completa si no es necesaria.

---

# 23. SOFT DELETE

Respetar la política del proyecto:

```text
is_active=False
is_deleted=True
```

cuando el modelo correspondiente tenga ambos campos.

No introducir hard delete para entidades que deban conservar trazabilidad.

Antes de eliminar físicamente cualquier código o registro, verificar dependencias.

---

# 24. ENDPOINTS LEGACY

Crear inventario:

| Endpoint | Consumidor | Estado |
|---|---|---|
| endpoint | frontend | ACTIVO |
| endpoint | panel legacy | LEGACY |
| endpoint | sin referencias | CANDIDATO |
| endpoint | integración externa | CONSERVAR |

No eliminar endpoint hasta verificar consumidores reales.

Si un endpoint es legacy pero todavía necesario:

```text
marcar deprecated
↓
migrar consumidor
↓
test
↓
eliminar
```

---

# 25. LIMPIEZA DE FRONTEND

Buscar:

- rutas no utilizadas;
- componentes no referenciados;
- modales duplicados;
- tablas duplicadas;
- stores antiguos;
- composables duplicados;
- imports muertos;
- funciones sin llamadas;
- eventos sin listeners;
- props sin consumidores;
- endpoints antiguos.

Registrar cada eliminación.

---

# 26. NO HACER

La IA editora NO debe:

- reescribir todo el módulo;
- cambiar arquitectura sin necesidad;
- crear una nueva aplicación Django solo para separar CRUD;
- cambiar modelos sin justificación;
- cambiar reglas de precio;
- cambiar estados de operaciones;
- cambiar flujo de pago;
- cambiar asignación de técnicos;
- eliminar ServiceOperation;
- eliminar fachada administrativa funcional;
- eliminar legacy sin verificar consumidores;
- cambiar contratos API innecesariamente;
- modificar datos históricos;
- introducir una segunda fuente de verdad.

---

# 27. ESTRATEGIA DE IMPLEMENTACIÓN POR FASES

## FASE 0 — BASELINE

Antes de modificar:

- ejecutar tests existentes;
- medir queries;
- medir tiempos;
- verificar CRUD;
- verificar frontend;
- registrar errores existentes.

Crear documento:

```text
SERVICES_OPTIMIZATION_BASELINE.md
```

---

## FASE 1 — AUDITORÍA

Generar:

```text
SERVICES_CODE_AUDIT.md
```

Debe contener:

- archivos;
- funciones;
- endpoints;
- componentes;
- stores;
- duplicaciones;
- código muerto;
- legacy;
- dependencias;
- riesgos.

No modificar todavía código crítico hasta finalizar esta fase.

---

## FASE 2 — OPTIMIZACIÓN SEGURA

Prioridad:

1. eliminar consultas duplicadas;
2. corregir cálculos repetidos;
3. optimizar serializers;
4. optimizar selectors;
5. reducir payload;
6. eliminar imports muertos;
7. eliminar helpers realmente sin uso.

---

## FASE 3 — SIMPLIFICACIÓN DEL CRUD

Consolidar:

```text
Service List
Service Form
Service Detail
Service API
Service State
```

Evitar duplicaciones.

Separar visualmente:

```text
CATÁLOGO
PRICING
OPERACIÓN
```

---

## FASE 4 — LEGACY

Auditar:

```text
OrderServiceDetail.technician
TechnicianAssignmentBoard.vue
```

y cualquier otro flujo antiguo.

Migrar consumidores antes de eliminar.

---

## FASE 5 — VALIDACIÓN

Ejecutar:

```text
CRUD tests
API tests
Serializer tests
Pricing tests
Operation tests
Assignment tests
Payment regression tests
Frontend tests
```

---

# 28. MATRIZ DE REGRESIÓN

Validar como mínimo:

## Catálogo

- crear servicio;
- editar servicio;
- listar;
- buscar;
- filtrar;
- activar;
- desactivar;
- eliminar lógicamente;
- visualizar detalle.

## Variantes

- crear;
- editar;
- eliminar;
- cambiar precio;
- consultar historial.

## Materiales

- asociar;
- editar;
- eliminar;
- verificar producto/variante.

## Pricing

- precio base;
- duración;
- costos;
- impuestos;
- descuentos;
- cotización.

## Checkout

- crear solicitud;
- iniciar pago;
- confirmar pago;
- liberar disponibilidad ante fallo.

## Operación

- crear operación;
- planificar;
- asignar;
- reasignar;
- cambiar estado;
- incidente;
- cierre;
- cancelación.

## Técnicos

- asignación automática;
- asignación manual;
- disponibilidad;
- especialidad/categoría.

---

# 29. CRITERIOS DE ACEPTACIÓN

La implementación solo se considera terminada cuando:

### Arquitectura

- [ ] CRUD separado conceptualmente de operación.
- [ ] Commands siguen siendo responsables de escrituras.
- [ ] Selectors siguen siendo responsables de lecturas.
- [ ] No existe lógica ORM innecesaria en Views.
- [ ] No se duplicó lógica de negocio.

### Performance

- [ ] baseline registrado;
- [ ] queries comparadas antes/después;
- [ ] cálculo de precio duplicado corregido;
- [ ] N+1 revisados;
- [ ] listado no carga datos innecesarios;
- [ ] payload reducido cuando sea posible.

### Código

- [ ] código muerto identificado;
- [ ] duplicaciones consolidadas;
- [ ] imports muertos eliminados;
- [ ] endpoints legacy clasificados;
- [ ] componentes frontend sin uso eliminados.

### Negocio

- [ ] pricing intacto;
- [ ] checkout intacto;
- [ ] pagos intactos;
- [ ] ServiceOperation intacto;
- [ ] asignación de técnicos intacta;
- [ ] FSM intacta;
- [ ] notificaciones intactas.

### Calidad

- [ ] tests existentes pasan;
- [ ] nuevos tests para cambios críticos;
- [ ] no hay errores nuevos;
- [ ] migraciones solo si son realmente necesarias;
- [ ] documentación actualizada.

---

# 30. FORMATO DE REPORTE FINAL DE LA IA EDITORA

Al terminar, generar:

```text
SERVICES_OPTIMIZATION_REPORT.md
```

Con:

## 1. Resumen

Qué se modificó.

## 2. Código eliminado

Archivo + función + motivo.

## 3. Código consolidado

Antes → después.

## 4. Queries

Comparación:

```text
ANTES: X queries
DESPUÉS: Y queries
MEJORA: Z%
```

## 5. Performance

Comparar:

```text
endpoint
latencia antes
latencia después
payload antes
payload después
```

## 6. CRUD

Estado de:

```text
LIST
CREATE
READ
UPDATE
DELETE
ACTIVATE
DEACTIVATE
```

## 7. Legacy

Qué quedó pendiente y por qué.

## 8. Riesgos

Cualquier deuda técnica restante.

## 9. Tests

Listado de pruebas ejecutadas y resultado.

---

# 31. REGLA FINAL PARA LA IA EDITORA

Trabajar de forma incremental.

Antes de cada cambio:

```text
INSPECCIONAR
↓
IDENTIFICAR DEPENDENCIAS
↓
MEDIR
↓
MODIFICAR
↓
TESTEAR
↓
MEDIR NUEVAMENTE
```

Nunca realizar una refactorización masiva sin comprobar el comportamiento existente.

La prioridad es:

```text
1. preservar negocio
2. preservar API
3. preservar datos
4. reducir consultas
5. reducir código duplicado
6. simplificar CRUD
7. retirar legacy de forma controlada
8. mejorar mantenibilidad
```

## Resultado esperado

El módulo Servicios debe quedar conceptualmente así:

```text
                    SERVICIOS
                       │
          ┌────────────┼────────────┐
          │            │            │
       CATÁLOGO      PRICING     OPERACIÓN
          │            │            │
      CRUD simple   Cotización   ServiceOperation
          │            │            │
      Servicios      Precios      Planificación
      Categorías     Costos       Técnicos
      Variantes      Impuestos    Estados
      Materiales     Descuentos   Incidentes
      Configuración                Notificaciones
```

El objetivo no es eliminar funcionalidades.

El objetivo es que **cada funcionalidad exista una sola vez, tenga una responsabilidad clara y se ejecute únicamente cuando sea necesaria.**
