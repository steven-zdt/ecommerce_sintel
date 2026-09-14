/**
 * resolveUrlNavigation — unica fuente de verdad para resolver un par
 * (url, url_type) a una accion de navegacion real (INTERNA/EXTERNA/ANCHOR).
 *
 * Usado por FeatureBannerButton.vue y CardItem.vue -- antes cada uno tenia su
 * propia logica (FeatureBannerButton ya usaba url_type explicito, CardItem.vue
 * inferia por regex `redirect_url.startsWith('http')`). Se centraliza aqui para
 * que un tercer componente con botones url_type no la reimplemente de nuevo.
 */
export function resolveUrlNavigation(url, urlType, router, target = '_self') {
  if (!url) return;
  if (urlType === 'EXTERNA') {
    if (target === '_blank') {
      window.open(url, '_blank', 'noopener,noreferrer');
    } else {
      window.location.href = url;
    }
    return;
  }
  if (urlType === 'ANCHOR') {
    const id = url.replace(/^#/, '');
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  // INTERNA (o cualquier valor no reconocido, por compatibilidad hacia atras)
  router.push(url);
}
