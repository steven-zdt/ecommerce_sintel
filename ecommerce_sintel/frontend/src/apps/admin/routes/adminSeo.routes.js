const SeoMetaTagList = () => import('@/modules/seo/SeoMetaTagList.vue');

export const adminSeoRoutes = [
  { path: 'seo/meta-tags', name: 'seo-meta-tags', component: SeoMetaTagList },
];
