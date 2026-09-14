# Card Group Section — Actualización del grafo de conocimiento

Fecha: 2026-08-06. Registro de qué nodos del grafo del proyecto cambian con esta extensión,
para que una futura auditoría (o agente) entienda que `HomeCard`/`HomeCardGroup` ahora
cubren el caso de uso "Card Group / Collection Section" sin necesidad de buscar un modelo
`CardGroupSection` separado que no existe.

## Nodos modificados (sin nodos nuevos)

```
core/models.py
  HomeCardGroup   [MODIFICADO] +8 campos (responsive + carrusel)
  HomeCard        [MODIFICADO] +9 campos (url_type, stats, boton secundario, badge_color)
                  [MODIFICADO] ahora tiene clean()/full_clean() en save() (antes no)

core/validators.py                         [NUEVO] validate_url_type_pair()
core/services/commands.py
  HomeCardGroupCommands.upsert/update       [MODIFICADO] whitelist +8 campos
  HomeCardCommands.create_card              [MODIFICADO] refactor kwargs -> **data+whitelist
  HomeCardCommands.update_card              [MODIFICADO] whitelist +9 campos
core/api/serializers.py
  HomeCardSerializer                        [MODIFICADO] +9 campos de salida
  HomeCardInputSerializer                   [MODIFICADO] +9 campos de entrada + sanitiza stats[]
  HomeCardGroupSerializer                   [MODIFICADO] +8 campos de salida
  HomeCardGroupInputSerializer              [MODIFICADO] +8 campos de entrada + FIX: ahora sanea HTML (antes no)
core/migrations/0029_card_group_section_fields.py  [NUEVO] + backfill de datos

dashboard/api/views.py
  AdminHomeCardViewSet.create_card          [MODIFICADO] delega a **data (antes kwargs explicitos)
  AdminHomeCardGroupViewSet.upsert          [MODIFICADO] extra tuple +8 campos
  AdminHomeCardGroupViewSet.update_group    [MODIFICADO] tuple +8 campos

frontend/src/utils/urlNavigation.js         [NUEVO] resolveUrlNavigation()
frontend/src/components/ui/showcase/FeatureBannerButton.vue  [MODIFICADO] usa el util nuevo (caso ANCHOR)
frontend/src/components/ui/home/cards/CardItem.vue           [MODIFICADO] navigate() + stats + boton secundario + badge_color
frontend/src/components/ui/home/cards/CardsGrid.vue          [MODIFICADO] columnas responsive reales (antes hardcodeadas)
frontend/src/components/ui/home/cards/CardsSlider.vue        [MODIFICADO] envuelve MarketplaceCarousel (antes scroll-snap manual)
frontend/src/renderers/SectionRenderer.vue                   [MODIFICADO] pasa `group` completo a los layouts
frontend/src/modules/core/home-builder/CardsSection.vue      [MODIFICADO] formularios de grupo/tarjeta ampliados
frontend/src/modules/core/HomeConfigView.vue                 [MODIFICADO] +regla CSS .hcb-subheading
```

## Dependencias cruzadas nuevas (por reutilización, no por duplicación)

```
CardItem.vue ────────────► urlNavigation.js ◄──────────── FeatureBannerButton.vue
CardsSlider.vue ─────────► MarketplaceCarousel.vue (ya usado por MarketplaceShowcase.vue)
CardsSlider.vue ─────────► MarketplaceIndicators.vue (idem)
HomeCard.clean() ────────► core/validators.py ◄──────────── FeatureBannerBlock.clean() (refactor)
```

Estas 4 flechas son la evidencia concreta de que "reutilizar completamente, no crear lógica
paralela" se cumplió con código real compartido, no solo con la intención declarada.

## Documentos relacionados que se mantienen vigentes (no requieren cambio)

- `core/.AGENT/docs/HOME_MODULE_GRAPH.md` — el grafo general del Home Builder no cambia de
  forma (`HomeCard`/`HomeCardGroup` seguían ahí); solo se referencian los campos nuevos desde
  este documento.
- `core/.AGENT/docs/FEATURE_BANNER_ARCHITECTURE.md` — se referencia como precedente directo
  del patrón `url_type`/`stats`, ahora generalizado a `core/validators.py`.
- `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` — la tabla de modelos de `core` no cambia
  de conteo (0 modelos nuevos); se debe actualizar solo el conteo de campos si esa tabla lo
  detalla por modelo (fuera del alcance de esta tarea puntual).
