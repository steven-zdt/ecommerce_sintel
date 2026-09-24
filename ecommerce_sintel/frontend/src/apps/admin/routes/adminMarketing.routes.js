const MarketingView = () => import('@/modules/marketing/MarketingView.vue');

export const adminMarketingRoutes = [
  { path: 'marketing', name: 'admin-marketing', component: MarketingView },
];
