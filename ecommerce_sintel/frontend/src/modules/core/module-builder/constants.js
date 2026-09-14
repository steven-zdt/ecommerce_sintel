// Constantes compartidas por mas de una pestana del ModuleBuilder.
// Las constantes usadas por UNA sola pestana viven dentro de su propio .vue.

// Usado por ResponsiveTab.vue (columnas por dispositivo, claves reales de `form`)
// y por CarouselTab.vue (items visibles por dispositivo).
export const DEVICES = [
  { key: 'columns',        icon: 'bi-display', label: 'Desktop' },
  { key: 'columns_tablet', icon: 'bi-tablet',  label: 'Tablet' },
  { key: 'columns_mobile', icon: 'bi-phone',   label: 'Mobile' },
];
