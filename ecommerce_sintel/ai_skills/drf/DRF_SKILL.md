# Sintel DRF Skill: Core Standards

Esta "Skill" define la metodología oficial para el desarrollo de APIs REST en Sintel, alineada con `GUIA_CONSTRUCCION.md`. Todo código generado para DRF debe seguir estos principios sin excepciones.

## Filosofía de Desarrollo

Aplicamos la arquitectura **"The Magnificent Four"** con un enfoque en **Arquitectura Limpia**:
1. **Modelos Anémicos**: Solo datos e integridad.
2. **Serializers Puros**: Solo transformación y validación.
3. **Services (Commands/Selectors)**: El único lugar para la lógica de negocio.
4. **ViewSets Orquestadores**: Solo manejo de protocolos HTTP.

## Reglas Obligatorias de Arquitectura

### 1. Prohibido el uso de Signals
Toda acción secundaria debe ser **explícita**. Si una orden debe descontar stock, el `OrderService` llama al `InventoryService` dentro de una transacción.

### 2. Capa de Servicios como SSoT (Single Source of Truth)
- `selectors.py`: Consultas GET optimizadas. Usar `.only()`, `select_related()` y `prefetch_related()` para evitar N+1.
- `commands.py`: Todas las mutaciones (POST, PUT, DELETE) dentro de `@transaction.atomic`.

### 3. ViewSets y Routers
- No usar `APIView` para CRUDs. Usar `ModelViewSet` o `GenericViewSet`.
- Registrar siempre las URLs en `urls.py` usando `DefaultRouter`.
- **Manejo de `swagger_fake_view`**: En `get_queryset()`, siempre retornar un queryset vacío si `getattr(self, 'swagger_fake_view', False)` es True para evitar errores durante la generación del esquema OpenAPI.

### 4. Seguridad y Anti-IDOR
- **UUID como Lookup**: Nunca exponer PKs enteros en URLs públicas. Usar el campo `uuid` de `SintelBaseModel`.
- **Filtro de Propiedad**: En `get_queryset`, siempre filtrar por `user=request.user` para recursos privados.
- **Enmascaramiento de Datos Sensibles**: Sobrescribir `to_representation` en serializers para ocultar tokens o secretos por defecto.

### 5. Serializers por Operación
- Separar serializers por responsabilidad cuando la lógica de lectura y escritura difiera significativamente: `<Model>ReadSerializer`, `<Model>CreateSerializer`, `<Model>UpdateSerializer`.
- Usar `@extend_schema_field` en `SerializerMethodField` para documentar tipos complejos en OpenAPI.

### 6. Respuestas Estandarizadas
- Todas las listas deben estar paginadas y seguir el formato: `{count, next, previous, results}`.
- Status codes correctos: `201` para creación, `204` para borrado, `403` para denegación de permisos.

## Integración
Este documento actúa como la ley fundamental del backend. Antes de proponer un cambio en DRF, verifica su cumplimiento con el `DRF_CHECKLIST.md`.
