/**
 * Resolver unico de imagenes (Auditoria Enterprise de Imagenes, 2026-08-04).
 * Centraliza la logica de "elegir la imagen principal" que antes estaba reimplementada de forma
 * identica en EquipmentHorizontalCard.vue, ServiceHorizontalCard.vue, ItemCard.vue y
 * ServiceCard.vue (los 4 hacian `images.find(i => i.is_primary) || images[0]` por separado).
 *
 * Las URLs que devuelve la API ya son absolutas (DRF ImageField + request.build_absolute_uri(),
 * verificado contra ecommerce/settings/base.py -- MEDIA_URL sin storage S3/CDN) -- este resolver
 * no concatena ninguna base URL, solo normaliza la FORMA del dato (string vs objeto) y elige
 * cual imagen mostrar.
 */

/**
 * Normaliza un solo item de imagen a una URL usable, o null si no hay nada renderizable.
 * Acepta las 2 formas que ya coexistian en el codebase: string directa, o objeto con
 * `.image`/`.url` (patron Shop/Renting/Services `ProductImage`/`EquipmentImage`/`ServiceImage`).
 * @param {string|{image?:string,url?:string}|null|undefined} image
 * @returns {string|null}
 */
export function resolveMediaUrl(image) {
  if (!image) return null;
  if (typeof image === 'string') return image || null;
  return image.image || image.url || null;
}

/**
 * Elige la imagen principal de un array: prioriza `is_primary`, si no hay ninguna marcada usa
 * la primera, si el array esta vacio/ausente retorna null.
 * @param {Array<{image?:string,url?:string,is_primary?:boolean}>|null|undefined} images
 * @returns {string|null}
 */
export function resolvePrimaryImage(images) {
  if (!images?.length) return null;
  const primary = images.find((img) => img?.is_primary);
  return resolveMediaUrl(primary || images[0]);
}
