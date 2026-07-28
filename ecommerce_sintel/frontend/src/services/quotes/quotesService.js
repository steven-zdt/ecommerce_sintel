import useApi from '@/composables/useApi';

export const quotesService = {
  templateCategories() {
    return useApi().get('quotes/quote-template-categories/').then(r => r.data);
  },
  templateSubcategories(categoryUuid) {
    return useApi().get(`quotes/quote-template-subcategories/?category=${categoryUuid}`).then(r => r.data);
  },
  templates() {
    return useApi().get('quotes/quote-templates/').then(r => r.data);
  },
  templateDetail(uuid) {
    return useApi().get(`quotes/quote-templates/${uuid}/`).then(r => r.data);
  },
  createFromTemplate(payload, idempotencyKey) {
    const config = idempotencyKey ? { headers: { 'X-Idempotency-Key': idempotencyKey } } : undefined;
    return useApi().post('quotes/quotations/from-template/', payload, config).then(r => r.data);
  },
  createFromCatalog(payload) {
    return useApi().post('quotes/quotations/', payload).then(r => r.data);
  },
};
