# Copilot Instructions for ecommerce_sintel_rest

Este repositorio sigue la logica y el contexto descrito en .claude y en ecommerce_sintel/CLAUDE.md.

## Reglas generales
- No usar emojis ni caracteres especiales Unicode en archivos Python.
- Revisar la documentacion de la app afectada antes de modificar codigo.
- Respetar patrones de Service Layer, permisos, soft delete y snapshots cuando aplique.
- Preferir cambios pequenos y dirigidos a la causa real del problema.

## Arquitectura
- Backend con Django, DRF, PostgreSQL, Redis, Celery y Channels.
- Frontend con Vue 3, Vite, Pinia y Vue Router.
- Autenticacion basada en JWT.
- Pagos integrados con Wompi.

## Validacion
- Verificar cambios con python -m py_compile cuando se editen archivos Python.
- Ejecutar python manage.py check o pytest cuando sea pertinente.

## Referencias utiles
- .copilot/README.md
- .copilot/project-context.md
- ecommerce_sintel/CLAUDE.md
