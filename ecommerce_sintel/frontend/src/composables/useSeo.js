// No hay libreria de head management instalada (vue-meta/@unhead/vue/@vueuse/head
// ausentes en package.json) -- se manipula document.head directamente. Unico
// punto de la app que hace esto, para no repetir el patron por vista.
export function useSeo() {
  function upsertMeta(name, content, attr = 'name') {
    if (!content) return;
    let tag = document.head.querySelector(`meta[${attr}="${name}"]`);
    if (!tag) {
      tag = document.createElement('meta');
      tag.setAttribute(attr, name);
      document.head.appendChild(tag);
    }
    tag.setAttribute('content', content);
  }

  function upsertJsonLd(obj) {
    if (!obj) return;
    let tag = document.head.querySelector('script[data-seo-jsonld]');
    if (!tag) {
      tag = document.createElement('script');
      tag.type = 'application/ld+json';
      tag.dataset.seoJsonld = 'true';
      document.head.appendChild(tag);
    }
    tag.textContent = JSON.stringify(obj);
  }

  function setSeo({ title, description, ogImage, jsonLd } = {}) {
    if (title) document.title = title;
    upsertMeta('description', description);
    upsertMeta('og:title', title, 'property');
    upsertMeta('og:description', description, 'property');
    upsertMeta('og:image', ogImage, 'property');
    upsertJsonLd(jsonLd);
  }

  return { setSeo };
}
