const MarketingView        = () => import('@/modules/marketing/MarketingView.vue');
const HomeConfigView       = () => import('@/modules/core/HomeConfigView.vue');
const AboutUsAdminView     = () => import('@/modules/core/AboutUsAdminView.vue');
const OrganizationView     = () => import('@/modules/organization/OrganizationView.vue');

export const adminCoreRoutes = [
  { path: 'marketing',    name: 'marketing',    component: MarketingView },
  { path: 'home-config',  name: 'home-config',  component: HomeConfigView },
  { path: 'nosotros',     name: 'about-us-admin', component: AboutUsAdminView },
  { path: 'organizacion', name: 'organization', component: OrganizationView },
];
