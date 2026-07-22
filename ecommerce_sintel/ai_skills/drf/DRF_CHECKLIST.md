# Sintel DRF Checklist: Validación de Código

Antes de aprobar cualquier cambio en el backend REST, verifica el cumplimiento de los siguientes puntos:

### 1. Estructura de Capas
- [ ] ¿La lógica de negocio reside en `services/commands.py`?
- [ ] ¿Las consultas personalizadas residen en `services/selectors.py`?
- [ ] ¿Se eliminaron todas las consultas ORM de `views.py`?
- [ ] ¿El ViewSet es una clase orquestadora pura?

### 2. Seguridad (Anti-IDOR y RBAC)
- [ ] ¿Se usa `uuid` en el `lookup_field` de la URL pública?
- [ ] ¿El `get_queryset` filtra por `user=request.user` para datos privados?
- [ ] ¿Se maneja `swagger_fake_view` en `get_queryset`?
- [ ] ¿Los permisos (`permission_classes`) son explícitos para cada acción?
- [ ] ¿Se enmascaran los datos sensibles en `to_representation`?

### 3. Rendimiento (Zero Waste)
- [ ] ¿Se usa `.select_related()` para ForeignKeys en listados?
- [ ] ¿Se usa `.prefetch_related()` para Many-to-Many o relaciones inversas?
- [ ] ¿Se usa `.only()` para traer solo los campos necesarios en el Selector?
- [ ] ¿Se eliminaron lazily-loaded queries dentro de bucles?

### 4. Serializers
- [ ] ¿El serializer está en `api/serializers.py`?
- [ ] ¿Se usan serializers específicos por acción si es necesario?
- [ ] ¿Se usa `@extend_schema_field` en todos los `SerializerMethodField`?
- [ ] ¿No contiene lógica de cálculo ni mutación de base de datos?

### 5. Routing y Endpoints
- [ ] ¿Se usa `DefaultRouter` en `urls.py`?
- [ ] ¿Sigue el patrón `/api/v1/<app>/`?
- [ ] ¿Se usa el método HTTP correcto (GET para lectura, POST para creación, etc.)?

### 6. Idempotencia y Signals
- [ ] ¿Se evitó el uso de `signals.py`?
- [ ] ¿El flujo de side-effects es explícito en el Command?
- [ ] ¿Las operaciones críticas son idempotentes?
