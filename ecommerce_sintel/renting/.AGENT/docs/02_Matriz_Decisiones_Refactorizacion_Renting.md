# Matriz de decisiones — Refactorización de Renting

| Candidato | Repetición observada | Diferencia que preserva cohesión | Decisión | Mejora medible | Riesgo |
|---|---|---|---|---|---|
| `models.py` monolítico | 35 modelos de siete subdominios | Ninguna: era una frontera de archivo, no de dominio | Extraer por módulo | 1 archivo de 1.734 líneas pasa a 11 módulos con responsabilidades explícitas | Bajo; API reexportada |
| Hijos simples del catálogo | FK a equipo, orden y activación | Texto/ícono, precio, FAQ y regla de presentación son semánticas distintas | Mantener separados | Evita discriminadores débiles y condicionales de serializer/admin | Alto si se fusiona: endpoints, permisos y payloads |
| Especificaciones | Patrón de hijo ordenado | Requieren grupo y orden de ficha técnica | Mantener `RentalSpecificationGroup` y `RentalSpecification` | Mantiene integridad y consultas por grupo | Alto si se aplana |
| Vídeo, documento e imagen | Contenido asociado a equipo | Tipos de recurso, archivo, portada, descarga y visibilidad son distintos | Mantener separados | Conserva validación/media y administración especializada | Alto si se unifica |
| Configuraciones de equipo | OneToOne con `Equipment` | Logística, oferta comercial y marketing tienen ciclo de vida y permisos propios | Mantener separados | Evita modelo ancho y campos mutuamente irrelevantes | Medio/alto si se consolida |
| Campos repetidos de catálogo | `equipment`, `position`, `is_active` | No existe comportamiento compartido adicional | No crear abstracta en esta pasada | No añade jerarquía ni riesgo de migración por ahorro superficial | Bajo al no cambiar |
| Compatibilidad de `RentalRequest` | Properties/setters hacia cuatro hijos | Es parte del contrato Python y de serializers/commands vigente | Mantener | Sin regresión de consumers; deuda visible y documentada | Alto si se elimina sin migrar todos los consumidores |
| `RentalCostRule` + asignación | Relación regla-variante | La asignación permite reutilizar una regla entre variantes del mismo equipo | Mantener | Conserva cardinalidad y selector de pricing | Alto si se colapsa |

## Decisión implementada

Se aprobó únicamente la división física del dominio. No cambia tablas, campos, restricciones, `app_label`, nombres públicos ni relaciones; por tanto no debe requerir una migración de esquema. Las decisiones restantes se declaran explícitamente **no implementadas** porque no cumplen el criterio de mejora arquitectónica sin un rediseño de contratos y una validación dinámica completa.
