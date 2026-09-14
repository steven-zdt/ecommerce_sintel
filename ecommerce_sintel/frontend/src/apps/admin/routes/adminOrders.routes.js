const OrderList     = () => import('@/modules/orders/OrderList.vue');
const RentalOperationBoard  = () => import('@/modules/renting/RentalOperationBoard.vue');
const OrderDetailView = () => import('@/modules/orders/views/OrderDetailView.vue');

// CRITICO: 'ordenes/renting' (estatico) DEBE preceder a 'ordenes/:uuid'
// (dinamico, mismo nivel) -- bug real historico (ver AUDITORIA/07_FRONTEND.md
// FE-C1): Vue Router hace match del primer patron que calza, asi que si el
// dinamico fuera antes, 'ordenes/renting' quedaria inalcanzable (interpretado
// como uuid='renting'). No reordenar estas 3 lineas.
export const adminOrdersRoutes = [
  { path: 'ordenes',        name: 'orders',            component: OrderList },
  { path: 'ordenes/renting', name: 'renting-operations', component: RentalOperationBoard },
  { path: 'ordenes/:uuid',  name: 'order-detail',      component: OrderDetailView },
];
