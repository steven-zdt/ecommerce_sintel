import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import useApi from '@/composables/useApi';

// Lazy-load de vistas para mejor rendimiento
const AdminLoginPage         = () => import('@/views/admin/AdminLoginPage.vue');
const AdminForgotPasswordView = () => import('@/views/admin/AdminForgotPasswordView.vue');
const LoginView              = () => import('@/views/auth/LoginView.vue');
const RegisterView           = () => import('@/views/auth/RegisterView.vue');
const ForgotPasswordView     = () => import('@/views/auth/ForgotPasswordView.vue');
const VerifyEmailLinkView    = () => import('@/views/auth/VerifyEmailLinkView.vue');
const AppShell      = () => import('@/components/layout/AppShell.vue');
const DashboardView = () => import('@/views/admin/DashboardView.vue');
const ProfileView   = () => import('@/views/admin/ProfileView.vue');
const ProductList   = () => import('@/modules/shop/ProductList.vue');
const CategoryList  = () => import('@/modules/shop/CategoryList.vue');
const BrandList     = () => import('@/modules/shop/BrandList.vue');
const TaxList       = () => import('@/modules/shop/TaxList.vue');
const OrderList     = () => import('@/modules/orders/OrderList.vue');
const OrderDetailView = () => import('@/modules/orders/views/OrderDetailView.vue');
const ShopOperationBoard = () => import('@/modules/orders/ShopOperationBoard.vue');
const UserList      = () => import('@/modules/users/UserList.vue');
// [2026-07-12] Movido de modules/accounts/ a modules/proveedores/ (CORE v4, Fase 6):
// es portafolio profesional de contratistas/tecnicos, no configuracion de cuenta/auth.
const ProfessionalsAdminList = () => import('@/modules/proveedores/ProfessionalsAdminList.vue');
const TechnicianAssignmentBoard = () => import('@/modules/technical_services/TechnicianAssignmentBoard.vue');
const ServiceOperationBoard = () => import('@/modules/technical_services/ServiceOperationBoard.vue');
const TechnicianCalendarBoard = () => import('@/modules/technical_services/TechnicianCalendarBoard.vue');
const TechnicianScheduleAdmin = () => import('@/modules/technical_services/TechnicianScheduleAdmin.vue');
const ServiceList           = () => import('@/modules/technical_services/ServiceList.vue');
const ServiceCategoryList   = () => import('@/modules/technical_services/ServiceCategoryList.vue');
const ServiceLevelList      = () => import('@/modules/technical_services/ServiceLevelList.vue');
const QuoteStudioView       = () => import('@/modules/quotes/QuoteStudioView.vue');
const QuoteTemplateBuilder  = () => import('@/modules/quotes/QuoteTemplateBuilder.vue');
const RentingList           = () => import('@/modules/renting/RentingList.vue');
const RentingRequestList    = () => import('@/modules/renting/RentingRequestList.vue');
const RentalOperationBoard  = () => import('@/modules/renting/RentalOperationBoard.vue');
const RentingCategoryList   = () => import('@/modules/renting/RentingCategoryList.vue');
const RentingBrandList      = () => import('@/modules/renting/RentingBrandList.vue');
const RentalLaborList       = () => import('@/modules/renting/RentalLaborList.vue');
const EquipmentDetailView   = () => import('@/modules/renting/EquipmentDetailView.vue');
const MarketingView        = () => import('@/modules/marketing/MarketingView.vue');
const HomeView             = () => import('@/views/customer/HomeView.vue');
const HomeConfigView       = () => import('@/modules/core/HomeConfigView.vue');
const AboutUsAdminView     = () => import('@/modules/core/AboutUsAdminView.vue');
const AboutUsView          = () => import('@/views/customer/AboutUsView.vue');
const ContactoView         = () => import('@/views/customer/ContactoView.vue');
const OrganizationView     = () => import('@/modules/organization/OrganizationView.vue');
const SupportDashboardView = () => import('@/modules/support/SupportDashboardView.vue');
const SecurityDashboardView = () => import('@/modules/security/SecurityDashboardView.vue');
const NotificationsAdminView = () => import('@/modules/notifications/NotificationsAdminView.vue');
const PaymentTransactionsAdminView = () => import('@/modules/payment/PaymentTransactionsAdminView.vue');
const OperationBoard      = () => import('@/modules/operations/OperationBoard.vue');
const OperationDetail     = () => import('@/modules/operations/OperationDetail.vue');
const DispatcherList      = () => import('@/modules/operations/DispatcherList.vue');
const OperationListView   = () => import('@/views/customer/operations/OperationListView.vue');
const OperationTrackingView = () => import('@/views/customer/operations/OperationTrackingView.vue');
const OperationalTasksView = () => import('@/views/operations/OperationalTasksView.vue');
const KycVerificationView = () => import('@/views/customer/account/KycVerificationView.vue');
const KycAdminList = () => import('@/modules/kyc/KycAdminList.vue');
const KycAdminDetail = () => import('@/modules/kyc/KycAdminDetail.vue');

// ── Customer Portal (portal del comprador) ─────────────────────────────────
const CustomerLayout        = () => import('@/components/customer/CustomerLayout.vue');
const ShopCatalogView       = () => import('@/views/customer/shop/ShopCatalogView.vue');
const ProductDetailView     = () => import('@/views/customer/detail/PublicDetailView.vue');
const RentalCatalogView       = () => import('@/views/customer/renting/RentalCatalogView.vue');
const RentalDetailView        = () => import('@/views/customer/detail/PublicDetailView.vue');
const RentalRequestWizard     = () => import('@/views/customer/renting/RentalBookingWizard.vue');
const RentalConfirmationView  = () => import('@/views/customer/renting/RentalConfirmationView.vue');
const RentalSuccessView       = () => import('@/views/customer/renting/RentalSuccessView.vue');
const MyRentalsView            = () => import('@/views/customer/renting/MyRentalsView.vue');
const ServicesCatalogView   = () => import('@/views/customer/services/ServicesCatalogView.vue');
const ServiceDetailView     = () => import('@/views/customer/detail/PublicDetailView.vue');
const ServiceRequestWizard  = () => import('@/views/customer/services/ServiceRequestWizard.vue');
const QuoteEntryView        = () => import('@/views/customer/quotes/QuoteEntryView.vue');
const QuoteWizardView       = () => import('@/views/customer/quotes/QuoteWizardView.vue');
const CatalogQuoteWizardView = () => import('@/views/customer/quotes/catalog/CatalogQuoteWizardView.vue');
const CustomerQuotesView    = () => import('@/views/customer/account/CustomerQuotesView.vue');
const CustomerProfileView   = () => import('@/views/customer/account/CustomerProfileView.vue');
const CustomerOrdersView    = () => import('@/views/customer/account/CustomerOrdersView.vue');
const ContractorOnboardingWizard = () => import('@/views/customer/account/ContractorOnboardingWizard.vue');
const CustomerWishlistView  = () => import('@/views/customer/account/CustomerWishlistView.vue');
const CustomerAddressView   = () => import('@/views/customer/account/CustomerAddressView.vue');
const CustomerCardsView     = () => import('@/views/customer/account/CustomerCardsView.vue');
const CheckoutView          = () => import('@/views/customer/checkout/CheckoutView.vue');
const OrderConfirmedView    = () => import('@/views/customer/checkout/OrderConfirmedView.vue');
const NequiPendingView      = () => import('@/views/customer/checkout/NequiPendingView.vue');
const PaymentResultView     = () => import('@/views/payment/PaymentResultView.vue');
const ContractorListView    = () => import('@/views/customer/contractors/ContractorListView.vue');
const PublicContractorProfileView = () => import('@/views/customer/contractors/PublicContractorProfileView.vue');
const ContractorScheduleView  = () => import('@/views/customer/account/ContractorScheduleView.vue');

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    // ── AUTH ──────────────────────────────────────────────────────────────────
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresGuest: true },
    },
    // Top-level (sin CustomerLayout): el rediseno usa su propio CustomerAuthLayout
    // de pantalla completa, no la navbar/footer de marketing (2026-07-17).
    { path: '/register', name: 'register', component: RegisterView, meta: { requiresGuest: true } },
    { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { requiresGuest: true } },
    // SSoT de identidad: todo registro publico crea siempre un CUSTOMER (ver
    // accounts/CLAUDE.md). Convertirse en profesional es un upgrade posterior
    // desde el dashboard ('contractor-onboarding'), no una eleccion en el
    // registro -- se conserva el redirect para no romper enlaces/marcadores
    // viejos a /registro-profesional.
    { path: '/registro-profesional', redirect: { name: 'register' } },
    {
      // Publica: sin requiresAuth ni requiresGuest -- el destinatario del enlace
      // de verificacion puede o no estar autenticado en este navegador.
      path: '/verificar-cuenta',
      name: 'verify-email-link',
      component: VerifyEmailLinkView,
    },

    // ── CUSTOMER PORTAL ───────────────────────────────────────────────────────
    {
      path: '/',
      component: CustomerLayout,
      children: [
        // Home publica
        { path: '',                          name: 'home',            component: HomeView },
        // Nosotros (filosofia institucional)
        { path: 'nosotros',                  name: 'about-us',        component: AboutUsView },
        // Contacto (datos de Organizacion, sin modelo/endpoint nuevo)
        { path: 'contacto',                  name: 'contact',         component: ContactoView },
        // Tienda
        { path: 'tienda',                    name: 'shop-catalog',    component: ShopCatalogView },
        { path: 'tienda/:uuid',              name: 'product-detail',  component: ProductDetailView },
        // Alquiler
        { path: 'alquiler',                            name: 'rental-catalog',  component: RentalCatalogView },
        { path: 'alquiler/:uuid',                      name: 'rental-detail',   component: RentalDetailView },
        { path: 'alquiler/:uuid/solicitar',            name: 'rental-request',  component: RentalRequestWizard, meta: { requiresAuth: true } },
        { path: 'alquiler/reserva/:uuid',              name: 'rental-confirmation', component: RentalConfirmationView, meta: { requiresAuth: true } },
        { path: 'alquiler/reserva/:uuid/exito',        name: 'rental-success', component: RentalSuccessView, meta: { requiresAuth: true } },
        // Servicios
        { path: 'servicios',                           name: 'services-catalog',  component: ServicesCatalogView },
        { path: 'servicios/:uuid',                     name: 'service-detail',    component: ServiceDetailView },
        { path: 'servicios/:uuid/solicitar',  name: 'service-request',      component: ServiceRequestWizard,    meta: { requiresAuth: true } },
        // Cotizaciones
        // - Catalogo: publica/anonima, precio inmediato "como estaba antes".
        // - Personalizada: requiere auth — ninguna solicitud se emite sin destinatario identificado.
        { path: 'cotizar',                   name: 'quote-entry',     component: QuoteEntryView },
        { path: 'cotizar/catalogo',          name: 'quote-catalog',   component: CatalogQuoteWizardView },
        { path: 'cotizar/personalizada',     name: 'quote-wizard',    component: QuoteWizardView,      meta: { requiresAuth: true } },
        // Checkout (requiere auth)
        { path: 'checkout',                  name: 'checkout',        component: CheckoutView,        meta: { requiresAuth: true } },
        { path: 'orden-confirmada',          name: 'order-confirmed', component: OrderConfirmedView },
        { path: 'payment/result',            name: 'payment-result',  component: PaymentResultView },
        { path: 'checkout/nequi-espera',      name: 'nequi-pending',   component: NequiPendingView,    meta: { requiresAuth: true } },
        // Contratistas / Marketplace
        { path: 'contratistas',        name: 'contractor-marketplace', component: ContractorListView },
        { path: 'contratistas/:uuid',  name: 'contractor-profile',     component: PublicContractorProfileView },
        { path: 'mis-tareas', name: 'operational-tasks', component: OperationalTasksView, meta: { requiresAuth: true } },
        // Mi cuenta (requiere auth)
        {
          path: 'mi-cuenta',
          redirect: '/mi-cuenta/perfil',
          meta: { requiresAuth: true },
          children: [
            { path: 'perfil',              name: 'customer-profile',       component: CustomerProfileView,         meta: { requiresAuth: true } },
            { path: 'pedidos',             name: 'customer-orders',        component: CustomerOrdersView,          meta: { requiresAuth: true } },
            { path: 'alquileres',           name: 'customer-rentals',       component: MyRentalsView,                meta: { requiresAuth: true } },
            { path: 'wishlist',            name: 'customer-wishlist',      component: CustomerWishlistView,        meta: { requiresAuth: true } },
            { path: 'direcciones',         name: 'customer-addresses',     component: CustomerAddressView,         meta: { requiresAuth: true } },
            { path: 'tarjetas',            name: 'customer-cards',         component: CustomerCardsView,           meta: { requiresAuth: true } },
            { path: 'cotizaciones',        name: 'customer-quotes',        component: CustomerQuotesView,          meta: { requiresAuth: true } },
            { path: 'perfil-profesional',  name: 'contractor-onboarding',  component: ContractorOnboardingWizard,  meta: { requiresAuth: true } },
            { path: 'verificacion',        name: 'kyc-verification',       component: KycVerificationView,         meta: { requiresAuth: true } },
            { path: 'mi-agenda',           name: 'contractor-schedule',    component: ContractorScheduleView,      meta: { requiresAuth: true } },
            { path: 'operaciones',         name: 'customer-operations',    component: OperationListView,            meta: { requiresAuth: true } },
            { path: 'operaciones/:uuid',   name: 'customer-operation-tracking', component: OperationTrackingView,   meta: { requiresAuth: true } },
          ],
        },
      ],
    },

    // ── PANEL ADMIN — login exclusivo (aislado de /login de clientes) ──────────
    // REGLA: esta ruta llama a api/v1/admin-auth/login/ únicamente.
    // No fusionar con /login ni con auth/login/. Ver AdminLoginPage.vue.
    {
      path: '/panel/login',
      name: 'admin-login',
      component: AdminLoginPage,
      meta: { requiresAdminGuest: true },
    },
    {
      path: '/panel/forgot-password',
      name: 'admin-forgot-password',
      component: AdminForgotPasswordView,
      meta: { requiresAdminGuest: true },
    },

    // ── PANEL ADMIN (protegido — requiere admin) ───────────────────────────────
    {
      path: '/panel',
      component: AppShell,
      meta: { requiresAuth: true, requiresAdmin: true },
      redirect: '/panel/dashboard',
      children: [
        { path: 'dashboard',    name: 'dashboard',    component: DashboardView },
        { path: 'perfil',       name: 'profile',      component: ProfileView },
        { path: 'productos',    name: 'product-list', component: ProductList },
        { path: 'productos/operaciones', name: 'shop-operations', component: ShopOperationBoard },
        { path: 'categorias',   name: 'category-list',component: CategoryList },
        { path: 'marcas',       name: 'brand-list',   component: BrandList },
        { path: 'impuestos',    name: 'tax-list',     component: TaxList },
        { path: 'ordenes',        name: 'orders',            component: OrderList },
        { path: 'ordenes/renting', name: 'renting-operations', component: RentalOperationBoard },
        { path: 'ordenes/:uuid',  name: 'order-detail',      component: OrderDetailView },
        { path: 'usuarios',     name: 'users-list',   component: UserList },
        { path: 'profesionales', name: 'professionals-admin-list', component: ProfessionalsAdminList },
        { path: 'validaciones',       name: 'kyc-admin-list',   component: KycAdminList },
        { path: 'validaciones/:uuid', name: 'kyc-admin-detail', component: KycAdminDetail },
        { path: 'servicios',          name: 'services',          component: ServiceList },
        { path: 's-categorias',       name: 'service-categories', component: ServiceCategoryList },
        { path: 's-niveles',          name: 'service-levels',     component: ServiceLevelList },
        { path: 'servicios/operaciones', name: 'service-operations', component: ServiceOperationBoard },
        { path: 'servicios/asignacion-tecnicos', name: 'technician-assignment-board', component: TechnicianAssignmentBoard },
        { path: 'servicios/agenda', name: 'technician-calendar', component: TechnicianCalendarBoard },
        { path: 'servicios/horarios', name: 'technician-schedule-admin', component: TechnicianScheduleAdmin },
        { path: 'cotizaciones',    name: 'quotes',           component: QuoteStudioView },
        { path: 'cotizaciones/plantillas/:uuid', name: 'quote-template-builder', component: QuoteTemplateBuilder },
        { path: 'renta',             name: 'renting',            component: RentingList },
        { path: 'renta/solicitudes', name: 'renting-requests',   component: RentingRequestList },
        { path: 'renta/:uuid',       name: 'equipment-detail',   component: EquipmentDetailView },
        { path: 'r-categorias',      name: 'renting-categories', component: RentingCategoryList },
        { path: 'r-marcas',          name: 'renting-brands',     component: RentingBrandList },
        { path: 'r-labor',           name: 'renting-labor',      component: RentalLaborList },
        { path: 'marketing',    name: 'marketing',    component: MarketingView },
        { path: 'home-config',  name: 'home-config',  component: HomeConfigView },
        { path: 'nosotros',     name: 'about-us-admin', component: AboutUsAdminView },
        { path: 'organizacion', name: 'organization', component: OrganizationView },
        { path: 'soporte',         name: 'support',          component: SupportDashboardView },
        { path: 'seguridad',      name: 'security',         component: SecurityDashboardView },
        { path: 'notificaciones', name: 'notifications-admin', component: NotificationsAdminView },
        { path: 'pagos',          name: 'payment-transactions', component: PaymentTransactionsAdminView },
        { path: 'operaciones',     name: 'admin-operations', component: OperationBoard },
        { path: 'operaciones/:uuid', name: 'admin-operation-detail', component: OperationDetail },
        { path: 'despachadores',   name: 'admin-dispatchers', component: DispatcherList },
      ],
    },

    // ── REDIRECT LEGACY ───────────────────────────────────────────────────────
    { path: '/panel/', redirect: '/panel/dashboard' },

    // ── CATCH-ALL ─────────────────────────────────────────────────────────────
    // Funcion en vez de `redirect: { name: 'home' }`: la forma objeto reutiliza
    // los params de la ruta no encontrada (incluye `pathMatch`), y como 'home'
    // no los declara, Vue Router los descarta con un warning en consola. Ver
    // https://github.com/vuejs/router/blob/main/packages/router/CHANGELOG.md#414-2022-08-22
    { path: '/:pathMatch(.*)*', redirect: () => ({ path: '/' }) },
  ],
});

// ── Guard de host (Fase 3, ADR-001: aislamiento de dominio del panel) ──────────
// panel.sintel.net.co debe servir EXCLUSIVAMENTE /panel/*; los demas dominios
// (sintel.net.co, www) ya no deben poder navegar a /panel/*. No se activa un
// bundle/build separado (ver ADR-001 §2) -- es el mismo router de siempre,
// solo con esta restriccion adicional evaluada antes que cualquier guard de
// auth. localhost/127.0.0.1 (dev) quedan exentos para no requerir dos
// dominios en desarrollo local.
const ADMIN_HOSTNAME = 'panel.sintel.net.co';
const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1'];

function isPanelPath(path) {
  return path === '/panel' || path.startsWith('/panel/');
}

// ── Navigation Guards ─────────────────────────────────────────────────────────
router.beforeEach(async (to) => {
  const hostname = window.location.hostname;
  if (!LOCAL_HOSTNAMES.includes(hostname)) {
    const isAdminHost = hostname === ADMIN_HOSTNAME;
    const targetIsPanel = isPanelPath(to.path);

    if (isAdminHost && !targetIsPanel) {
      // panel.sintel.net.co no sirve nada fuera de /panel/*.
      return { path: '/panel/dashboard' };
    }

    if (!isAdminHost && targetIsPanel) {
      // Purga cualquier sesion (de cliente o de staff) que hubiera quedado
      // en este origen antes de saltar al panel -- nunca debe quedar residuo
      // de una sesion de admin reflejado en sintel.net.co (bug real: el login
      // publico dejaba tokens de staff en este origen antes de este guard
      // redirigir). A-05 (auditoria enterprise): antes limpiaba ambos
      // storages a mano (localStorage/sessionStorage.removeItem por clave),
      // un tercer camino de limpieza de sesion fuera del store de auth --
      // usar authStore.logout() unifica con useApi.js (que ya lo usa en sus
      // 2 puntos de fallo de refresh/401) y ademas limpia el estado en
      // memoria de Pinia (accessToken/user), no solo el storage.
      useAuthStore().logout();
      // El dominio publico ya no sirve el panel. Redirige preservando el
      // path completo (incluye query/hash via fullPath) para no romper
      // bookmarks/enlaces antiguos a sintel.net.co/panel/* (ADR-001 D2).
      window.location.replace(`https://${ADMIN_HOSTNAME}${to.fullPath}`);
      return false;
    }
  }

  // Recuperacion PSE: cuando el navegador regresa despues de la redireccion bancaria,
  // sessionStorage conserva el UUID de la transaccion pendiente.
  // Lo interceptamos aqui y mandamos al usuario directamente a /payment/result.
  const pendingTx = sessionStorage.getItem('wompi_pending_tx');
  if (pendingTx && to.path !== '/payment/result') {
    sessionStorage.removeItem('wompi_pending_tx');
    return { path: '/payment/result', query: { tx: pendingTx } };
  }

  const authStore = useAuthStore();

  // Sincronizar perfil si los datos de sesion no tienen is_staff (localStorage viejo)
  if (authStore.isAuthenticated && authStore.user?.is_staff === undefined) {
    try {
      const api = useApi();
      const { data } = await api.get('auth/profile/');
      authStore.setUser(data);
    } catch (_) {
      authStore.logout();
      return { name: 'admin-login' };
    }
  }

  // Refrescar perfil al entrar al dashboard del cliente -- asi un upgrade
  // aprobado (user_type/kyc_status) se refleja en el menu/sidebar sin
  // necesidad de relogin (no existe infraestructura WebSocket para esto).
  if (authStore.isAuthenticated && to.path.startsWith('/mi-cuenta')) {
    try {
      const api = useApi();
      const { data } = await api.get('auth/profile/');
      authStore.setUser(data);
    } catch (_) {
      // Silencioso -- si falla, el usuario sigue con los datos que ya tenia
    }
  }

  // 1. Ruta del panel admin requiere auth -> admin-login (ruta aislada)
  if (to.meta.requiresAuth && to.meta.requiresAdmin && !authStore.isAuthenticated) {
    return { name: 'admin-login' };
  }

  // 2. Ruta requiere auth genérica (clientes) y no autenticado -> login cliente
  if (to.meta.requiresAuth && !to.meta.requiresAdmin && !authStore.isAuthenticated) {
    return { name: 'login' };
  }

  // 3. Ruta requiere admin y esta autenticado pero no es admin -> tienda
  if (to.meta.requiresAdmin && authStore.isAuthenticated && !authStore.isAdmin) {
    return { name: 'shop-catalog' };
  }

  // 4. /panel/login con admin ya autenticado -> dashboard directo
  if (to.meta.requiresAdminGuest && authStore.isAuthenticated && authStore.isAdmin) {
    return { name: 'dashboard' };
  }

  // 5. Ruta de guest (login/register) con usuario autenticado -> su area
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return authStore.isAdmin ? { name: 'dashboard' } : { name: 'shop-catalog' };
  }
});

export default router;
