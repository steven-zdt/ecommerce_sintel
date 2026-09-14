const RentingList           = () => import('@/modules/renting/RentingList.vue');
const RentingRequestList    = () => import('@/modules/renting/RentingRequestList.vue');
const EquipmentDetailView   = () => import('@/modules/renting/EquipmentDetailView.vue');
const RentingCategoryList   = () => import('@/modules/renting/RentingCategoryList.vue');
const RentingBrandList      = () => import('@/modules/renting/RentingBrandList.vue');
const RentalLaborList       = () => import('@/modules/renting/RentalLaborList.vue');

// 'renta/solicitudes' (estatico) antes de 'renta/:uuid' (dinamico, mismo
// nivel) -- mismo patron de riesgo que ordenes/renting vs ordenes/:uuid, no
// reordenar.
export const adminRentingRoutes = [
  { path: 'renta',             name: 'renting',            component: RentingList },
  { path: 'renta/solicitudes', name: 'renting-requests',   component: RentingRequestList },
  { path: 'renta/:uuid',       name: 'equipment-detail',   component: EquipmentDetailView },
  { path: 'r-categorias',      name: 'renting-categories', component: RentingCategoryList },
  { path: 'r-marcas',          name: 'renting-brands',     component: RentingBrandList },
  { path: 'r-labor',           name: 'renting-labor',      component: RentalLaborList },
];
