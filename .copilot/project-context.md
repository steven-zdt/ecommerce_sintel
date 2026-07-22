# Contexto de proyecto - ecommerce_sintel_rest

## Resumen general
Este repositorio contiene un proyecto de e-commerce basado en Django y DRF, con modularizacion por aplicaciones y un frontend moderno separado o integrado segun el modulo.

## Arquitectura principal
- Backend: Django 4, Django REST Framework, PostgreSQL, Redis, Celery y Channels.
- Frontend: Vue 3, Vite, Pinia, Vue Router y Axios.
- Autenticacion: JWT con email como USERNAME_FIELD.
- Pagos: integracion con Wompi para Colombia.

## Estructura clave
- Proyecto Django principal: ecommerce_sintel/
- Aplicaciones principales: accounts, cart, core, ecommerce, inventory, marketing, notifications, operations, orders, payment, quotes, renting, shipping, shop, support, technical_services, users.
- Documentacion y arquitectura por app: ecommerce_sintel/<app>/CLAUDE.md y archivos .AGENT/docs.

## Reglas de trabajo
- No usar emojis ni caracteres especiales Unicode en archivos Python.
- Leer la documentacion especifica de cada app antes de modificar codigo.
- Mantener patrones de Service Layer, permisos, soft delete y snapshots cuando aplique.
- Validar cambios con comandos como:
  - python -m py_compile <archivo.py>
  - python manage.py check
  - pytest

## Puntos criticos
- El proyecto depende mucho de la organizacion por modulos y de la coherencia entre backend y frontend.
- Los cambios en modelos, APIs o reglas de negocio deben revisarse con contexto de la app correspondiente.
- La documentacion local de cada modulo debe tomarse como fuente de verdad antes de implementar.
