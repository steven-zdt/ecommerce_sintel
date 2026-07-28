// Transforma la lista cruda de store.cardGroups (HomeCardGroup) en los dos mapas
// que CardsSection.vue y el panel de preview compartido (HomeConfigView.vue)
// necesitan: nombre -> titulo, nombre -> config completa. Funcion pura -- ambos
// consumidores la derivan directo de store.cardGroups via un computed, sin
// sincronizar estado duplicado entre componentes (P1-3, 2026-07-27).
export function buildGroupMaps(cardGroups) {
  const titleMap = {};
  const configMap = {};
  for (const g of cardGroups) {
    titleMap[g.name] = g.title;
    configMap[g.name] = g;
  }
  return { titleMap, configMap };
}
