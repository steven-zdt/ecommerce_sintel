// Mismo mapa curado que core/api/serializers.py::ICON_SHORTHAND_MAP -- se usa
// solo para la vista previa instantanea en el panel; el backend es la fuente
// de verdad y normaliza de nuevo al guardar.
export const ICON_SHORTHAND_MAP = {
  telephone: 'bi-telephone', house: 'bi-house', facebook: 'bi-facebook',
  instagram: 'bi-instagram', linkedin: 'bi-linkedin', shop: 'bi-shop',
  camera: 'bi-camera-video', shield: 'bi-shield-check', alarm: 'bi-bell',
  building: 'bi-building', people: 'bi-people', truck: 'bi-truck',
};

export function normalizeIconInput(value) {
  const v = (value || '').trim();
  if (!v) return '';
  if (v.startsWith('bi-')) return v;
  return ICON_SHORTHAND_MAP[v] || `bi-${v}`;
}
