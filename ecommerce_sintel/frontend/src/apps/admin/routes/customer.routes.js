// Portal del comprador (CustomerLayout: navbar+footer+carrito+chat de
// soporte). Un solo route object con arbol de children -- se mantiene entero
// (no se subdivide mas) porque toda la jerarquia comparte el mismo padre
// CustomerLayout y dividirla en sub-arreglos no reduce complejidad real.
const CustomerLayout        = () => import('@/components/customer/CustomerLayout.vue');
const HomeView              = () => import('@/views/customer/HomeView.vue');
const AboutUsView           = () => import('@/views/customer/AboutUsView.vue');
const ContactoView          = () => import('@/views/customer/ContactoView.vue');
const ShopCatalogView       = () => import('@/views/customer/shop/ShopCatalogView.vue');
const ProductDetailView     = () => import('@/views/customer/detail/PublicDetailView.vue');
const RentalCatalogView       = () => import('@/views/customer/renting/RentalCatalogView.vue');
const RentalDetailView        = () => import('@/views/customer/detail/PublicDetailView.vue');
const RentalRequestWizard     = () => import('@/views/customer/renting/RentalBookingWizard.vue');
const RentalConfirmationView  = () => import('@/views/customer/renting/RentalConfirmationView.vue');
const RentalSuccessView       = () => import('@/views/customer/renting/RentalSuccessView.vue');
const ServicesCatalogView   = () => import('@/views/customer/services/ServicesCatalogView.vue');
const ServiceDetailView     = () => import('@/views/customer/detail/PublicDetailView.vue');
const ServiceRequestWizard  = () => import('@/views/customer/services/ServiceRequestWizard.vue');
const QuoteEntryView        = () => import('@/views/customer/quotes/QuoteEntryView.vue');
const QuoteWizardView       = () => import('@/views/customer/quotes/QuoteWizardView.vue');
const CatalogQuoteWizardView = () => import('@/views/customer/quotes/catalog/CatalogQuoteWizardView.vue');
const CheckoutView          = () => import('@/views/customer/checkout/CheckoutView.vue');
const OrderConfirmedView    = () => import('@/views/customer/checkout/OrderConfirmedView.vue');
const NequiPendingView      = () => import('@/views/customer/checkout/NequiPendingView.vue');
const PaymentResultView     = () => import('@/views/payment/PaymentResultView.vue');
const ContractorListView    = () => import('@/views/customer/contractors/ContractorListView.vue');
const PublicContractorProfileView = () => import('@/views/customer/contractors/PublicContractorProfileView.vue');
const OperationalTasksView = () => import('@/views/operations/OperationalTasksView.vue');
const CustomerProfileView   = () => import('@/views/customer/account/CustomerProfileView.vue');
const CustomerOrdersView    = () => import('@/views/customer/account/CustomerOrdersView.vue');
const MyRentalsView            = () => import('@/views/customer/renting/MyRentalsView.vue');
const CustomerWishlistView  = () => import('@/views/customer/account/CustomerWishlistView.vue');
const CustomerAssistantMemoryView = () => import('@/views/customer/account/CustomerAssistantMemoryView.vue');
const CustomerAddressView   = () => import('@/views/customer/account/CustomerAddressView.vue');
const CustomerCardsView     = () => import('@/views/customer/account/CustomerCardsView.vue');
const CustomerQuotesView    = () => import('@/views/customer/account/CustomerQuotesView.vue');
const CustomerSupportTicketView = () => import('@/views/customer/account/CustomerSupportTicketView.vue');
const ContractorOnboardingWizard = () => import('@/views/customer/account/ContractorOnboardingWizard.vue');
const KycVerificationView = () => import('@/views/customer/account/KycVerificationView.vue');
const ContractorScheduleView  = () => import('@/views/customer/account/ContractorScheduleView.vue');
const OperationListView   = () => import('@/views/customer/operations/OperationListView.vue');
const OperationTrackingView = () => import('@/views/customer/operations/OperationTrackingView.vue');

export const customerRoutes = {
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
        { path: 'memoria-asistente',   name: 'customer-assistant-memory', component: CustomerAssistantMemoryView, meta: { requiresAuth: true } },
        { path: 'direcciones',         name: 'customer-addresses',     component: CustomerAddressView,         meta: { requiresAuth: true } },
        { path: 'tarjetas',            name: 'customer-cards',         component: CustomerCardsView,           meta: { requiresAuth: true } },
        { path: 'cotizaciones',        name: 'customer-quotes',        component: CustomerQuotesView,          meta: { requiresAuth: true } },
        { path: 'soporte',             name: 'customer-support-ticket', component: CustomerSupportTicketView,  meta: { requiresAuth: true } },
        { path: 'perfil-profesional',  name: 'contractor-onboarding',  component: ContractorOnboardingWizard,  meta: { requiresAuth: true } },
        { path: 'verificacion',        name: 'kyc-verification',       component: KycVerificationView,         meta: { requiresAuth: true } },
        { path: 'mi-agenda',           name: 'contractor-schedule',    component: ContractorScheduleView,      meta: { requiresAuth: true } },
        { path: 'operaciones',         name: 'customer-operations',    component: OperationListView,            meta: { requiresAuth: true } },
        { path: 'operaciones/:uuid',   name: 'customer-operation-tracking', component: OperationTrackingView,   meta: { requiresAuth: true } },
      ],
    },
  ],
};
