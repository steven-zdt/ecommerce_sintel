"""
AI Gateway — punto unico de entrada HTTP del AI Core (Componente 2 del plan).

Todas las rutas de negocio del motor viven bajo /api/v1/ai/* y exigen el JWT
real de Django (ver auth.py). Los endpoints historicos de generacion de
codigo (/generate, /plan, /impact, ...) NO se tocan -- este paquete es la
capa nueva y paralela.

Versionado (Componente 12): el prefijo /api/v1/ es parte del contrato desde
el dia uno; una v2 futura convive como router nuevo, nunca rompe v1.
"""
from gateway.router import ai_router

__all__ = ["ai_router"]
