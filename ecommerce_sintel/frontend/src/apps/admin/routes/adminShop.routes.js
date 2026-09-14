const ProductList   = () => import('@/modules/shop/ProductList.vue');
const ShopOperationBoard = () => import('@/modules/orders/ShopOperationBoard.vue');
const CategoryList  = () => import('@/modules/shop/CategoryList.vue');
const BrandList     = () => import('@/modules/shop/BrandList.vue');
const TaxList       = () => import('@/modules/shop/TaxList.vue');

// Children de /panel (AppShell) -- se insertan tal cual, orden interno
// preservado. No hay pares estatico/dinamico del mismo nivel en este grupo,
// asi que el orden entre estas 5 no es sensible a shadowing.
export const adminShopRoutes = [
  { path: 'productos',    name: 'product-list', component: ProductList },
  { path: 'productos/operaciones', name: 'shop-operations', component: ShopOperationBoard },
  { path: 'categorias',   name: 'category-list',component: CategoryList },
  { path: 'marcas',       name: 'brand-list',   component: BrandList },
  { path: 'impuestos',    name: 'tax-list',     component: TaxList },
];
