const QuoteStudioView       = () => import('@/modules/quotes/QuoteStudioView.vue');
const QuoteTemplateBuilder  = () => import('@/modules/quotes/QuoteTemplateBuilder.vue');

export const adminQuotesRoutes = [
  { path: 'cotizaciones',    name: 'quotes',           component: QuoteStudioView },
  { path: 'cotizaciones/plantillas/:uuid', name: 'quote-template-builder', component: QuoteTemplateBuilder },
];
