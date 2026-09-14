const ServiceList           = () => import('@/modules/technical_services/ServiceList.vue');
const ServiceCategoryList   = () => import('@/modules/technical_services/ServiceCategoryList.vue');
const ServiceLevelList      = () => import('@/modules/technical_services/ServiceLevelList.vue');
const ServiceOperationBoard = () => import('@/modules/technical_services/ServiceOperationBoard.vue');
const ServiceRequestsPanel  = () => import('@/modules/technical_services/ServiceRequestsPanel.vue');
const TechnicianAssignmentBoard = () => import('@/modules/technical_services/TechnicianAssignmentBoard.vue');
const TechnicianCalendarBoard = () => import('@/modules/technical_services/TechnicianCalendarBoard.vue');
const TechnicianScheduleAdmin = () => import('@/modules/technical_services/TechnicianScheduleAdmin.vue');

export const adminServicesRoutes = [
  { path: 'servicios',          name: 'services',          component: ServiceList },
  { path: 's-categorias',       name: 'service-categories', component: ServiceCategoryList },
  { path: 's-niveles',          name: 'service-levels',     component: ServiceLevelList },
  // Plan "Fachada Administrativa Unificada" (2026-08-14) -- fachada de
  // lectura/escritura sobre orders.Order + technical_services.ServiceOperation,
  // sin ownership propio (ver technical_services/.AGENT/SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md).
  { path: 'servicios/solicitudes', name: 'service-requests', component: ServiceRequestsPanel },
  { path: 'servicios/operaciones', name: 'service-operations', component: ServiceOperationBoard },
  { path: 'servicios/asignacion-tecnicos', name: 'technician-assignment-board', component: TechnicianAssignmentBoard },
  { path: 'servicios/agenda', name: 'technician-calendar', component: TechnicianCalendarBoard },
  { path: 'servicios/horarios', name: 'technician-schedule-admin', component: TechnicianScheduleAdmin },
];
