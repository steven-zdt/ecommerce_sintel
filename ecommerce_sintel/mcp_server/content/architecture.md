# SINTEL E-Commerce - arquitectura (resumen para clientes MCP)

Stack: Django 5 + DRF + PostgreSQL + Redis + Celery + Channels (backend), Vue 3 + Vite + Pinia (frontend), JWT (simplejwt, email como usuario), pagos Wompi Colombia.

## Principios que el MCP respeta (no los reimplementa)
- **API-first**: el panel admin es un BFF sobre `/api/v1/dashboard/`. Los ViewSets delegan en Orchestrators y estos en Commands/Selectors (Service Layer).
- **Django es la autoridad final**: autenticacion (JWT), permisos (`IsAdminUser` = `is_staff AND is_superuser`), validacion de negocio y capa de servicio.
- **Borrado logico**: los dominios usan soft-delete (`is_deleted`/`is_active=False`); no hay DELETE fisico en el CRUD.
- **Snapshots y precios**: los precios, IVA, envios, reservas de inventario y transiciones de pedido son logica de negocio de Django. El MCP nunca las calcula.

## Dominios
shop (productos, categorias, marcas, impuestos), services (servicios tecnicos), renting (equipos de alquiler), orders, quotes, marketing, support, inventory, users, payment,
notifications, ai_provider (proveedores de IA), ai_engine_adk (chat de soporte con Google ADK), ai_editor (propuestas de cambio de codigo con aprobacion humana).

## Este servidor MCP
Adapter/orquestador de solo lo anterior: descubre la API (`api.describe`), lee y administra recursos registrados (`crud.*`), y lee codigo del workspace de solo lectura (`code.*`).
No tiene acceso a PostgreSQL, Redis, shell, Docker ni filesystem irrestricto.
