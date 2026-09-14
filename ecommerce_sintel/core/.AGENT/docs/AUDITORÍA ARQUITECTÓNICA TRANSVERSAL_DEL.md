AUDITORÍA ARQUITECTÓNICA TRANSVERSAL DEL ERP SINTEL
CONTEXTO

Actúa como un equipo compuesto por:

Enterprise Software Architect
Principal Software Engineer
Django Enterprise Expert
Vue 3 Enterprise Expert
PostgreSQL Architect
DRF API Architect
Clean Architecture Specialist
Domain Driven Design Specialist
Software Auditor
Performance Engineer
Security Auditor
Technical Documentation Specialist

Tu misión NO es desarrollar nuevas funcionalidades.

Tu misión es certificar que toda la arquitectura del ERP SINTEL es consistente, utilizando como Single Source of Truth (SSoT) la documentación arquitectónica oficial de cada módulo, comenzando por Core, y verificando que el resto del sistema esté alineado con ella.

Debes preservar completamente la lógica de negocio existente.

No debes introducir cambios funcionales.

No debes romper contratos API.

No debes romper el frontend.

No debes modificar flujos de negocio.

No debes eliminar características.

Solo puedes:

auditar
documentar
detectar inconsistencias
proponer mejoras
ejecutar refactorizaciones seguras cuando sean aprobadas.
OBJETIVOS

La auditoría debe certificar que el sistema completo cumple:

Clean Architecture
SOLID
DRY
KISS
YAGNI
Service Layer Pattern
Command Pattern
Selector Pattern
Contract First API
Single Source of Truth
Arquitectura Modular
Bajo Acoplamiento
Alta Cohesión
MÓDULOS A AUDITAR

Tomar como referencia la arquitectura oficial y reconstruir el mapa completo de dependencias entre:

Core
Organization
Accounts
Shop
Renting
Technical Services
Payments
Notifications
Marketing
SEO
Quotes
Dashboard
Frontend SPA
AI Engine
Shared
Utils

Nunca asumir que dos documentos están sincronizados. Debes verificarlo.

FASE 1 — RECONSTRUCCIÓN DEL GRAFO EMPRESARIAL

Antes de modificar cualquier archivo:

Reconstruir automáticamente:

Backend
Apps
Models
Managers
QuerySets
Selectors
Commands
Services
ViewSets
URLs
Middleware
Permissions
Signals
Cache
Tasks
Validators
Storage
Frontend
Views
Pages
Router
Components
Shared Components
Renderers
Stores
Composables
API Client
Formularios
Modales
Integraciones
AI Engine
Organization
Marketing
Payments
SEO
Notifications
Entregables

Generar:

PROJECT_GRAPH.md

PROJECT_DEPENDENCIES.md

PROJECT_CONTEXT.md

API_GRAPH.md

FRONTEND_GRAPH.md

AI_ENGINE_GRAPH.md
FASE 2 — AUDITORÍA DE DOCUMENTACIÓN

Comparar automáticamente:

Documentación

↓

Código

↓

Implementación

↓

Frontend

↓

API

↓

Base de datos

Buscar:

documentación desactualizada
documentación incompleta
modelos no documentados
serializers no documentados
endpoints sin documentación
frontend sin documentación
documentación deprecada
referencias cruzadas rotas
contradicciones entre documentos

No modificar código todavía.

Entregable
DOCUMENTATION_AUDIT.md
FASE 3 — AUDITORÍA DE DEPENDENCIAS

Reconstruir el árbol completo de dependencias.

Detectar:

imports circulares
dependencias ocultas
dependencias innecesarias
dependencias duplicadas
violaciones SOLID
acoplamiento fuerte
dependencias transitivas peligrosas
referencias cruzadas inválidas

Clasificar:

CRÍTICO

ALTO

MEDIO

BAJO

Entregable
DEPENDENCY_AUDIT.md
FASE 4 — AUDITORÍA DEL SERVICE LAYER

Verificar que TODA la lógica pase únicamente por:

Selectors

Commands

Services

Buscar lógica indebida en:

Views

Serializers

Models

Signals

Validators

Forms

Middleware

Generar

SERVICE_LAYER_AUDIT.md
FASE 5 — AUDITORÍA DE CONTRATOS API

Reconstruir automáticamente:

Frontend

↓

API

↓

ViewSet

↓

Serializer

↓

Command

↓

Selector

↓

Model

↓

Database

Detectar:

contratos duplicados
endpoints muertos
endpoints sin consumidores
consumidores inexistentes
serializers redundantes
DTO duplicados
propiedades sin utilizar
contratos inconsistentes

Generar

API_CONTRACT_AUDIT.md
FASE 6 — AUDITORÍA FRONTEND

Buscar todos los consumidores.

Verificar:

componentes muertos
componentes duplicados
renderizadores duplicados
llamadas API repetidas
estados innecesarios
props sin uso
stores sin consumidores
composables duplicados
imports innecesarios

Generar

FRONTEND_AUDIT.md
FASE 7 — AUDITORÍA DE RENDIMIENTO

Analizar:

consultas N+1
select_related
prefetch_related
annotate
Exists
Subquery
índices
cache
Redis
TTL
consultas repetidas
serialización innecesaria
payload excesivo

Generar

PERFORMANCE_AUDIT.md
FASE 8 — AUDITORÍA DE SEGURIDAD

Validar:

JWT
permisos
autorización
autenticación
CSRF
CORS
XSS
uploads
archivos
media
rate limiting
exposición de datos
mass assignment
validaciones

Generar

SECURITY_AUDIT.md
FASE 9 — AUDITORÍA DE DEUDA TÉCNICA

Detectar:

código muerto
clases sin uso
serializers sin consumidores
ViewSets sin rutas
migraciones obsoletas
TODO
FIXME
HACK
XXX
Legacy
Deprecated

Generar

TECHNICAL_DEBT.md
FASE 10 — PLAN DE REFACTORIZACIÓN

No modificar código todavía.

Construir un plan ordenado por prioridad:

Prioridad 1

Problemas críticos.

Prioridad 2

Problemas altos.

Prioridad 3

Problemas medios.

Prioridad 4

Problemas bajos.

Cada recomendación debe incluir:

motivo técnico
módulos afectados
riesgo
beneficio
impacto
archivos involucrados
estrategia de rollback
validaciones posteriores

Generar

REFACTOR_MASTER_PLAN.md
FASE 11 — IMPLEMENTACIÓN CONTROLADA

Solo después de aprobar el plan:

Implementar cambios en pequeños lotes.

Después de cada lote ejecutar automáticamente:

Validación de imports.
Validación de migraciones.
Validación de contratos API.
Validación del frontend.
Validación del AI Engine.
Validación de caché.
Validación de permisos.
Validación de compatibilidad.
Validación de documentación.

Si algún cambio rompe un contrato o un consumidor, revertir ese lote y registrar el incidente antes de continuar.

FASE 12 — CERTIFICACIÓN FINAL

Generar un informe ejecutivo con:

Estado arquitectónico del ERP.
Cumplimiento de principios de diseño.
Mapa de dependencias actualizado.
Riesgos eliminados.
Riesgos pendientes.
Deuda técnica restante.
Cobertura de la auditoría.
Archivos modificados.
Métricas antes/después.
Recomendaciones para la siguiente iteración.
CRITERIOS DE ACEPTACIÓN

La auditoría solo se considerará finalizada cuando:

Toda la documentación esté alineada con el código.
Todos los contratos API estén validados con sus consumidores.
No existan dependencias circulares.
No existan inconsistencias entre backend, frontend y documentación.
Todos los cambios sean compatibles con la arquitectura oficial de SINTEL.
Cada hallazgo incluya evidencia verificable (archivo, clase, método o endpoint) y una propuesta de resolución priorizada.
Se entregue la documentación técnica generada en todas las fases.

Este enfoque aprovecha la documentación actualizada del módulo Core como referencia canónica y extiende la auditoría al resto del ERP, reduciendo el riesgo de divergencias entre módulos y permitiendo una refactorización controlada del sistema completo