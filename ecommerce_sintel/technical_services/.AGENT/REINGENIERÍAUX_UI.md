# PLAN_SERVICES_DETAIL_ENTERPRISE.md

# REINGENIERÍA UX/UI DEL MÓDULO TECHNICAL SERVICES

## Enterprise Service Detail Experience (ESDX)

---

# OBJETIVO GENERAL

Transformar completamente la página de detalle del servicio (Service Detail Page - SDP) del módulo Technical Services en una experiencia Enterprise de clase mundial, inspirada en la organización de información utilizada por grandes plataformas de servicios y comercio electrónico.

El objetivo NO es copiar el diseño visual de ningún sitio web.

El objetivo es construir una experiencia mucho más clara, profesional, técnica y administrable que permita al cliente comprender completamente el servicio antes de solicitarlo.

La solución debe mantener intacta toda la lógica de negocio documentada en la arquitectura oficial del módulo.

---

# PRINCIPIOS

NO modificar:

* Commands
* Selectors
* Service Layer
* API
* Endpoints
* DTO
* Serializer
* Workflow Operativo
* Sistema de Cotización
* Sistema de Operaciones
* Asignación de Técnicos
* Sistema de Pagos
* Scheduler
* Disponibilidad
* Marketplace
* Pricing Engine

Toda la intervención será únicamente sobre la administración del contenido y la experiencia visual.

---

# OBJETIVOS FUNCIONALES

La nueva Service Detail Page deberá:

• Explicar claramente el servicio.

• Generar confianza.

• Reducir incertidumbre.

• Mostrar todo el alcance.

• Facilitar la decisión de compra.

• Mostrar documentación técnica.

• Explicar el proceso de prestación.

• Mostrar garantías.

• Mostrar cobertura.

• Mostrar requisitos.

• Mejorar la experiencia móvil.

• Reducir la carga cognitiva.

---

# FASE 1

## Auditoría Arquitectónica

Objetivo

Analizar completamente el módulo Technical Services.

Tareas

* Auditar arquitectura.

* Auditar componentes.

* Auditar APIs.

* Auditar DTO.

* Auditar Serializers.

* Auditar rutas.

* Auditar componentes Frontend.

* Auditar duplicaciones.

* Auditar deuda técnica.

* Construir Knowledge Graph.

Entregables

✓ Informe técnico

✓ Grafo de dependencias

✓ Componentes reutilizables

✓ Riesgos

No escribir código.

---

# FASE 2

## Auditoría UX

Analizar:

ServiceDetail

Hero

Galería

Tabs

Cards

Timeline

Ficha Técnica

FAQ

Documentos

Videos

Materiales

Servicios relacionados

Detectar problemas.

Documentar oportunidades de mejora.

---

# FASE 3

## Nueva Arquitectura de Información

Eliminar la descripción larga.

Convertir toda la información en bloques.

Orden recomendado

1.

Resumen Ejecutivo

2.

Descripción del Servicio

3.

Alcance

4.

Beneficios

5.

Qué incluye

6.

Qué NO incluye

7.

Proceso del servicio

8.

Cómo trabajamos

9.

Materiales utilizados

10.

Cobertura

11.

Tiempo estimado

12.

Requisitos del cliente

13.

Instalación

14.

Soporte

15.

Garantía

16.

Técnicos especializados

17.

Ficha técnica

18.

Documentos

19.

Videos

20.

Preguntas frecuentes

21.

Servicios relacionados

22.

Productos recomendados

23.

Casos de éxito

Todos independientes.

Todos administrables.

---

# FASE 4

## Diseño del CMS

Modificar únicamente el administrador del servicio.

Agregar pestaña:

Contenido Enterprise

El administrador podrá construir el detalle mediante bloques.

No utilizar HTML manual.

Todo mediante formularios.

---

# FASE 5

## Constructor de Bloques

Implementar bloques reutilizables.

Descripción

Imagen + Texto

Galería

Lista

Beneficios

Alcance

Incluye

No incluye

Proceso

Timeline

Tabla

Documento

Video

FAQ

Cobertura

Garantía

Personalizado

Cada bloque tendrá:

Título

Subtítulo

Imagen

Icono

Contenido

Orden

Visible

Publicado

---

# FASE 6

## Hero Enterprise

Rediseñar completamente el Hero.

Debe mostrar:

Servicio

Categoría

Nivel

Precio

Tiempo estimado

Disponibilidad

Botón Solicitar

Galería

Indicadores

Badges

Resumen

No modificar la lógica.

---

# FASE 7

## Alcance

Crear componente especializado.

Permitir:

Imagen

Descripción

Lista

Iconografía

Notas

Advertencias

---

# FASE 8

## Qué Incluye

Cada elemento permitirá:

Imagen

Icono

Texto

Orden

Visible

---

# FASE 9

## Qué NO Incluye

Mismo funcionamiento.

Mostrar claramente exclusiones.

---

# FASE 10

## Proceso del Servicio

Crear un componente visual que explique paso a paso cómo se presta el servicio.

Cada paso podrá tener:

Número

Título

Descripción

Imagen

Tiempo estimado

---

# FASE 11

## Materiales Utilizados

Aprovechar la información existente del módulo.

Mostrar:

Material

Cantidad

Imagen

Descripción

Compatibilidad

No duplicar datos.

Consumir la información existente.

---

# FASE 12

## Cobertura

Crear bloque administrable.

Mostrar:

Ciudades

Zonas

Cobertura

Restricciones

---

# FASE 13

## Instalación

Explicar:

Preparación

Tiempo

Condiciones

Requisitos

Herramientas

---

# FASE 14

## Soporte

Mostrar:

Canales

Horario

Cobertura

Garantía

SLA

Mantenimiento

---

# FASE 15

## Técnicos Especializados

Crear bloque informativo.

Mostrar:

Especialidades

Certificaciones

Experiencia

No exponer información sensible.

---

# FASE 16

## Ficha Técnica

Eliminar tablas HTML.

Crear constructor dinámico.

Agrupar por categorías.

General

Operación

Materiales

Cobertura

Compatibilidad

Garantía

---

# FASE 17

## Documentación

Administrar:

Manual

Ficha Técnica

PDF

Certificados

Normativas

Catálogos

---

# FASE 18

## Videos

Permitir:

YouTube

Vimeo

Videos propios

Miniaturas

Descripción

---

# FASE 19

## FAQ

Crear acordeón reutilizable.

Pregunta

Respuesta

Orden

Publicado

---

# FASE 20

## Servicios Relacionados

Mostrar automáticamente servicios compatibles.

No duplicar consultas.

Consumir relaciones existentes.

---

# FASE 21

## Productos Relacionados

Consumir información del módulo Shop.

Mostrar materiales o productos asociados sin romper el desacoplamiento entre módulos.

---

# FASE 22

## Responsive

Optimizar:

Desktop

Tablet

Mobile

Las tablas deberán convertirse en tarjetas.

---

# FASE 23

## Accesibilidad

Garantizar:

HTML semántico.

ARIA.

Contraste.

Teclado.

Lectores de pantalla.

---

# FASE 24

## Rendimiento

Implementar:

Lazy Loading.

Lazy Images.

Intersection Observer.

Skeleton Loading.

Carga diferida.

Optimización Lighthouse.

---

# FASE 25

## Auditoría Final

Validar:

Compatibilidad arquitectónica.

No romper APIs.

No romper Commands.

No romper Selectors.

No romper Pricing Engine.

No romper ServiceOperation.

No romper Marketplace.

No romper Scheduler.

No romper DTO.

No romper Frontend existente.

Eliminar duplicaciones.

Reducir deuda técnica.

---

# ENTREGABLES

✓ Auditoría completa del módulo.

✓ Knowledge Graph actualizado.

✓ Mapa de componentes.

✓ Plan de migración.

✓ Arquitectura objetivo.

✓ Checklist técnico.

✓ Checklist UX.

✓ Checklist Responsive.

✓ Plan de pruebas.

✓ Riesgos.

✓ Estrategia de rollback.

✓ Validación final de que el módulo mantiene la arquitectura Enterprise documentada y está preparado para reutilizar la misma infraestructura de contenido en Shop, Renting y futuros módulos del ecosistema.
