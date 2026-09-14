/**
 * Composable para manejar Structured Data (JSON-LD) para SEO.
 * Soporta: Product, AggregateRating, Review, Organization, BreadcrumbList.
 */
import { useAppConfigStore } from '@/store/appConfig';

// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado en 4 lugares --
// ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_FRONTEND_AUDIT.md. appConfigStore ya
// esta cargado en la practica (fetchConfig() corre desde CustomerLayout/
// AppShell antes de que se rendericen las vistas que llaman estas funciones),
// pero se degrada con gracia si no -- '' en vez de un nombre de marca falso.
function currentBrandName() {
  return useAppConfigStore().brand.site_name || '';
}

/**
 * Genera JSON-LD para Product con todos los detalles.
 */
export function generateProductSchema(equipment) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: equipment.hero?.name,
    description: equipment.hero?.description,
    image: [
      equipment.media?.gallery?.principal?.url,
      ...(equipment.media?.gallery?.principal_images?.map(img => img.url) || []),
    ].filter(Boolean),
    brand: {
      '@type': 'Brand',
      name: equipment.hero?.brand_name || currentBrandName(),
    },
    category: equipment.hero?.category_name,
    offers: {
      '@type': 'Offer',
      url: typeof window !== 'undefined' ? window.location.href : '',
      priceCurrency: 'COP',
      price: equipment.pricing?.price_per_day,
      availability: equipment.availability?.status === 'available'
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      inventoryLevel: equipment.availability?.available_now,
      seller: {
        '@type': 'Organization',
        name: currentBrandName(),
      },
    },
    aggregateRating: equipment.reviews?.average_rating ? {
      '@type': 'AggregateRating',
      ratingValue: equipment.reviews.average_rating,
      ratingCount: equipment.reviews.total_count,
      bestRating: '5',
      worstRating: '1',
    } : undefined,
    review: (equipment.reviews?.items || []).slice(0, 5).map(review => ({
      '@type': 'Review',
      author: {
        '@type': 'Person',
        name: review.user_name,
      },
      datePublished: review.created_at,
      description: review.comment,
      reviewRating: {
        '@type': 'Rating',
        ratingValue: review.rating,
        bestRating: '5',
        worstRating: '1',
      },
    })),
  };
}

/**
 * Genera JSON-LD para BreadcrumbList (navegación).
 */
export function generateBreadcrumbSchema(breadcrumbs) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: `${typeof window !== 'undefined' ? window.location.origin : ''}${item.url}`,
    })),
  };
}

/**
 * Genera JSON-LD para Organization (en el header/footer).
 */
// NOTA (white-label F7, 2026-08-14): esta funcion no se llama desde ningun
// componente hoy (grep confirmado) -- logo/sameAs/contactPoint seguian
// siendo datos de ejemplo (sintel.example.com, telefono ficticio) que nunca
// se conectaron a organization.Branding/SocialLink/ContactInfo reales. Se
// corrige `name` por consistencia con el resto del archivo, pero conectar
// logo/redes/contacto reales queda pendiente si esta funcion llega a usarse.
export function generateOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: currentBrandName(),
    url: typeof window !== 'undefined' ? window.location.origin : '',
    logo: 'https://sintel.example.com/logo.png',
    sameAs: [
      'https://www.facebook.com/sintel',
      'https://www.instagram.com/sintel',
      'https://www.linkedin.com/company/sintel',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'Customer Service',
      email: 'soporte@sintel.com',
      telephone: '+57 1 1234 5678',
    },
  };
}

/**
 * Inyecta JSON-LD en el head del documento.
 */
export function injectJsonLd(schema) {
  if (typeof document === 'undefined') return;

  const script = document.createElement('script');
  script.type = 'application/ld+json';
  script.textContent = JSON.stringify(schema);

  const head = document.head || document.documentElement;
  head.appendChild(script);

  return () => head.removeChild(script); // Cleanup function
}

/**
 * Genera Open Graph meta tags para social sharing.
 */
export function generateOpenGraphTags(equipment) {
  return {
    'og:type': 'website',
    'og:title': equipment.seo?.meta_title || equipment.hero?.name,
    'og:description': equipment.seo?.meta_description || equipment.hero?.description,
    'og:image': equipment.seo?.og_image_url || equipment.media?.gallery?.principal?.url,
    'og:url': typeof window !== 'undefined' ? window.location.href : '',
    'og:site_name': currentBrandName(),
  };
}

/**
 * Genera Twitter Card meta tags.
 */
export function generateTwitterCardTags(equipment) {
  return {
    'twitter:card': 'summary_large_image',
    'twitter:title': equipment.seo?.meta_title || equipment.hero?.name,
    'twitter:description': equipment.seo?.meta_description || equipment.hero?.description,
    'twitter:image': equipment.seo?.og_image_url || equipment.media?.gallery?.principal?.url,
    'twitter:site': '@sintel',
    'twitter:creator': '@sintel',
  };
}

/**
 * SEO Score: 0-100 basado en presencia de elementos clave.
 */
export function calculateSeoScore(equipment) {
  let score = 0;

  // Meta tags
  if (equipment.seo?.meta_title) score += 10;
  if (equipment.seo?.meta_description) score += 10;
  if (equipment.seo?.meta_keywords) score += 5;

  // Content
  if (equipment.hero?.name?.length >= 50) score += 5;
  if (equipment.hero?.description?.length >= 120) score += 10;

  // Images
  if (equipment.media?.gallery?.principal) score += 10;
  if (equipment.media?.gallery?.all_images?.length >= 3) score += 10;

  // Structured data
  if (equipment.reviews?.average_rating) score += 10;
  if (equipment.reviews?.total_count >= 5) score += 5;

  // Technical
  if (equipment.media?.videos?.length > 0) score += 5;
  if (equipment.seo?.og_image_url) score += 5;

  // Schema
  if (equipment.hero?.category_name) score += 5;

  return Math.min(score, 100);
}
