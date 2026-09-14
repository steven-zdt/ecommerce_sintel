import useApi from '@/composables/useApi';

export const shopService = {
  list(params = {}) {
    return useApi().get('shop/products/', { params }).then(r => r.data);
  },
  categories() {
    return useApi().get('shop/categories/').then(r => r.data);
  },
  brands() {
    return useApi().get('shop/brands/').then(r => r.data);
  },
  detail(uuid) {
    return useApi().get(`shop/products/${uuid}/detail/`).then(r => r.data);
  },
  reviews(uuid) {
    return useApi().get(`shop/products/${uuid}/reviews/`).then(r => r.data);
  },
  addReview(uuid, payload) {
    return useApi().post(`shop/products/${uuid}/review/`, payload).then(r => r.data);
  },
};
