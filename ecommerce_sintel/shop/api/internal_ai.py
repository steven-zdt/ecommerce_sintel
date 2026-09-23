"""
Rutas internas /api/v1/internal/ai/catalog/* -- consumidas SOLO por el AI
Engine (Admin AI Assistant, vertical piloto Catalogo, Fase 3, 2026-09-16).

Ver ai_engine/.AGENT/ADMIN_AI_ASSISTANT_FASE0_MATRIZ.md (inventario real de
capacidades) y ADMIN_AI_ASSISTANT_FASE1_TOOLS_CATALOGO.md (catalogo de Tools
+ clasificacion de riesgo) para el diseno completo de esta vertical.

Cubre Product (Nivel 0-3 completo: lectura, borrador, mutacion auditada,
publicacion con HITL) y Category/Brand/Tax (mismo patron, agregado en la
misma sesion). Delete (Nivel 4) NO se implementa aqui a proposito en NINGUN
dominio -- sin esos endpoints, eliminar cualquier entidad via el AI
Assistant es fisicamente imposible todavia, no solo una regla de prompt.

Mismo patron que core/api/internal_ai.py: cada vista envuelve exclusivamente
Selectors/Commands ya existentes de shop/services/, permission_classes real
de Django (users.api.permissions.IsAdminUser, is_staff AND is_superuser) como
autoridad final, auditoria via SecurityEvent en toda escritura.
"""
from django.db.models import Q
from django.http import Http404
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from ecommerce.internal_ai_utils import log_ai_action as _log_ai_action
from shop.models import Product, Tax
from shop.services.commands import BrandCommands, CategoryCommands, ProductCommands, TaxCommands
from shop.services.selectors import BrandSelector, CategorySelector, ProductSelector, TaxSelector
from users.api.permissions import IsAdminUser


def _default_variant(product):
    return (
        product.variants.filter(is_deleted=False, is_default=True).first()
        or product.variants.filter(is_deleted=False).first()
    )


def _serialize_product(product) -> dict:
    variant = _default_variant(product)
    return {
        'uuid': str(product.uuid),
        'name': product.name,
        'slug': product.slug,
        'is_active': product.is_active,
        'is_featured': product.is_featured,
        'condition': product.condition,
        'short_description': product.short_description,
        'description': product.description,
        'scope': product.scope,
        'warranty': product.warranty,
        'category': (
            {'uuid': str(product.category.uuid), 'name': product.category.name}
            if product.category_id else None
        ),
        'brand': (
            {'uuid': str(product.brand.uuid), 'name': product.brand.name}
            if product.brand_id else None
        ),
        'price': str(variant.price) if variant else None,
        'discounted_price': str(variant.discounted_price) if variant and variant.discounted_price else None,
        'stock': variant.stock if variant else None,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
    }


class AiCatalogProductListView(APIView):
    """GET /api/v1/internal/ai/catalog/products/ -- lectura, sin auditoria (Nivel 0)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ProductSelector.list_all_for_admin()
        search = request.query_params.get('search')
        is_active = request.query_params.get('is_active')
        is_featured = request.query_params.get('is_featured')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(short_description__icontains=search))
        if is_active in ('true', 'false'):
            qs = qs.filter(is_active=is_active == 'true')
        if is_featured in ('true', 'false'):
            qs = qs.filter(is_featured=is_featured == 'true')
        try:
            limit = min(int(request.query_params.get('limit', 20)), 50)
        except (TypeError, ValueError):
            limit = 20
        products = list(qs[:limit])
        return Response({'count': len(products), 'products': [_serialize_product(p) for p in products]})


class AiCatalogProductGetView(APIView):
    """GET /api/v1/internal/ai/catalog/products/get/?uuid=... -- lectura, sin auditoria (Nivel 0)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            product = ProductSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Producto no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_product(product))


class AiCatalogProductCreateDraftView(APIView):
    """
    POST /api/v1/internal/ai/catalog/products/create-draft/ -- Nivel 1 (borrador).

    Regla dura (Decision 1 y 2 del catalogo de Tools, Fase 1): un producto
    creado por esta via SIEMPRE nace is_active=False y stock=0, sin importar
    lo que pida el payload -- publicar es una Tool separada (Nivel 3, HITL,
    no implementada todavia) y cargar stock real es una operacion explicita
    aparte (update-draft), nunca implicita en la creacion de un borrador
    (create_product() escribe stock real en Inventory via
    InventoryCommands.register_entry si stock > 0 -- ver shop/services/
    commands.py -- inaceptable para un Nivel 1 "sin publicar").
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        data = request.data
        name = (data.get('name') or '').strip()
        category_uuid = data.get('category')
        price = data.get('price')
        if not name or not category_uuid or price in (None, ''):
            return Response(
                {'error': 'name, category y price son requeridos.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            category = CategorySelector.get_by_uuid(category_uuid)
        except Http404:
            return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        brand = None
        brand_uuid = data.get('brand')
        if brand_uuid:
            try:
                brand = BrandSelector.get_by_uuid(brand_uuid)
            except Http404:
                return Response({'error': 'Marca no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            product = ProductCommands.create_product(
                vendor=request.user,
                category=category,
                name=name,
                price=price,
                condition=data.get('condition') or Product.Condition.NEW,
                short_description=data.get('short_description'),
                description=data.get('description', ''),
                video_url=data.get('video_url'),
                scope=data.get('scope', ''),
                warranty=data.get('warranty', ''),
                brand=brand,
                is_active=False,   # SIEMPRE -- ver docstring de la clase.
                is_featured=bool(data.get('is_featured', False)),
                stock=0,           # SIEMPRE -- ver docstring de la clase.
                meta_title=data.get('meta_title', ''),
                meta_description=data.get('meta_description', ''),
            )
        except (TypeError, ValueError) as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)

        product = ProductSelector.get_by_uuid(product.uuid)
        _log_ai_action(request, 'CatalogProductCreateDraftTool', {'product_uuid': str(product.uuid), 'name': name})
        return Response(_serialize_product(product), status=http_status.HTTP_201_CREATED)


class AiCatalogProductUpdateDraftView(APIView):
    """
    POST /api/v1/internal/ai/catalog/products/update-draft/ -- Nivel 2 (mutacion auditada).

    Edita contenido/categoria/marca/precio/stock de un producto YA
    EXISTENTE (borrador o publicado). NUNCA acepta `is_active` -- publicar/
    despublicar es una Tool separada (set_published_state, Nivel 3, HITL
    obligatorio, todavia no implementada). `is_active` se descarta aqui
    aunque llegue en el payload, como segunda capa de defensa (la primera es
    que el Tool schema del lado del LLM ni siquiera declara ese campo).
    """
    permission_classes = [IsAdminUser]

    _ALLOWED_FIELDS = ProductCommands.PRODUCT_ALLOWED_FIELDS - {'is_active'}
    _VARIANT_FIELDS = ('price', 'discounted_price', 'stock')

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            product = ProductSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Producto no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        data = {k: v for k, v in request.data.items() if k in self._ALLOWED_FIELDS}
        for field in self._VARIANT_FIELDS:
            if field in request.data:
                data[field] = request.data[field]

        if 'category' in data:
            try:
                data['category'] = CategorySelector.get_by_uuid(data['category'])
            except Http404:
                return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)
        if 'brand' in data:
            try:
                data['brand'] = BrandSelector.get_by_uuid(data['brand']) if data['brand'] else None
            except Http404:
                return Response({'error': 'Marca no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            updated = ProductCommands.update_product(product, data)
        except (TypeError, ValueError) as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)

        updated = ProductSelector.get_by_uuid(updated.uuid)
        _log_ai_action(request, 'CatalogProductUpdateDraftTool', {'product_uuid': str(updated.uuid), 'fields': list(data.keys())})
        return Response(_serialize_product(updated))


class AiCatalogProductSetPublishedStateView(APIView):
    """
    POST /api/v1/internal/ai/catalog/products/set-published-state/ -- Nivel 3.

    UNICA via por la que este agente puede cambiar `is_active`. Payload
    restringido a exactamente ese campo (Decision 1 del catalogo de Tools,
    Fase 1) -- nunca acepta ningun otro campo de contenido en la misma
    llamada, para que publicar/despublicar sea siempre una accion aislada,
    explicita y auditable por separado de una edicion de contenido. Del lado
    del agente (CatalogProductSetPublishedStateTool, ai_engine/tools/
    catalog_tools.py) esta Tool tiene requires_confirmation=True -- ADK pausa
    el turno y exige que el administrador confirme antes de que esta vista
    llegue a ejecutarse.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        is_active = request.data.get('is_active')
        if not uuid or not isinstance(is_active, bool):
            return Response(
                {'error': 'uuid e is_active (booleano) son requeridos.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            product = ProductSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Producto no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        updated = ProductCommands.update_product(product, {'is_active': is_active})
        updated = ProductSelector.get_by_uuid(updated.uuid)
        _log_ai_action(
            request, 'CatalogProductSetPublishedStateTool',
            {'product_uuid': str(updated.uuid), 'is_active': is_active},
        )
        return Response(_serialize_product(updated))


# ─── Category (mismo patron que Product: Nivel 0-3) ────────────────────────

def _serialize_category(category) -> dict:
    return {
        'uuid': str(category.uuid),
        'name': category.name,
        'slug': category.slug,
        'description': category.description,
        'is_active': category.is_active,
        'parent': {'uuid': str(category.parent.uuid), 'name': category.parent.name} if category.parent_id else None,
        'meta_title': category.meta_title,
        'meta_description': category.meta_description,
    }


class AiCatalogCategoryListView(APIView):
    """GET /api/v1/internal/ai/catalog/categories/ -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = CategorySelector.list_all_for_admin()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search))
        try:
            limit = min(int(request.query_params.get('limit', 20)), 50)
        except (TypeError, ValueError):
            limit = 20
        categories = list(qs[:limit])
        return Response({'count': len(categories), 'categories': [_serialize_category(c) for c in categories]})


class AiCatalogCategoryGetView(APIView):
    """GET /api/v1/internal/ai/catalog/categories/get/?uuid=... -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            category = CategorySelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_category(category))


class AiCatalogCategoryCreateDraftView(APIView):
    """POST /api/v1/internal/ai/catalog/categories/create-draft/ -- Nivel 1, is_active=False forzado."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'error': 'name requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        parent = None
        parent_uuid = request.data.get('parent')
        if parent_uuid:
            try:
                parent = CategorySelector.get_by_uuid(parent_uuid)
            except Http404:
                return Response({'error': 'Categoria padre no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        category = CategoryCommands.create_category(
            name=name,
            description=request.data.get('description', ''),
            parent=parent,
            is_active=False,  # SIEMPRE -- publicar es una Tool separada (set-published-state).
            meta_title=request.data.get('meta_title', ''),
            meta_description=request.data.get('meta_description', ''),
        )
        _log_ai_action(request, 'CatalogCategoryCreateDraftTool', {'category_uuid': str(category.uuid), 'name': name})
        return Response(_serialize_category(category), status=http_status.HTTP_201_CREATED)


class AiCatalogCategoryUpdateView(APIView):
    """POST /api/v1/internal/ai/catalog/categories/update/ -- Nivel 2, is_active excluido."""
    permission_classes = [IsAdminUser]

    _ALLOWED_FIELDS = CategoryCommands.CATEGORY_ALLOWED_FIELDS - {'is_active', 'image'}

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            category = CategorySelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)

        data = {k: v for k, v in request.data.items() if k in self._ALLOWED_FIELDS}
        if 'parent' in data:
            try:
                data['parent'] = CategorySelector.get_by_uuid(data['parent']) if data['parent'] else None
            except Http404:
                return Response({'error': 'Categoria padre no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)

        updated = CategoryCommands.update_category(category, data)
        _log_ai_action(request, 'CatalogCategoryUpdateTool', {'category_uuid': str(updated.uuid), 'fields': list(data.keys())})
        return Response(_serialize_category(updated))


class AiCatalogCategorySetPublishedStateView(APIView):
    """POST /api/v1/internal/ai/catalog/categories/set-published-state/ -- Nivel 3, HITL."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        is_active = request.data.get('is_active')
        if not uuid or not isinstance(is_active, bool):
            return Response({'error': 'uuid e is_active (booleano) son requeridos.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            category = CategorySelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
        updated = CategoryCommands.update_category(category, {'is_active': is_active})
        _log_ai_action(request, 'CatalogCategorySetPublishedStateTool', {'category_uuid': str(updated.uuid), 'is_active': is_active})
        return Response(_serialize_category(updated))


# ─── Brand (mismo patron, sin parent/meta) ──────────────────────────────────

def _serialize_brand(brand) -> dict:
    return {'uuid': str(brand.uuid), 'name': brand.name, 'slug': brand.slug, 'is_active': brand.is_active}


class AiCatalogBrandListView(APIView):
    """GET /api/v1/internal/ai/catalog/brands/ -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = BrandSelector.list_all_for_admin()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search))
        try:
            limit = min(int(request.query_params.get('limit', 20)), 50)
        except (TypeError, ValueError):
            limit = 20
        brands = list(qs[:limit])
        return Response({'count': len(brands), 'brands': [_serialize_brand(b) for b in brands]})


class AiCatalogBrandGetView(APIView):
    """GET /api/v1/internal/ai/catalog/brands/get/?uuid=... -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            brand = BrandSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Marca no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_brand(brand))


class AiCatalogBrandCreateDraftView(APIView):
    """POST /api/v1/internal/ai/catalog/brands/create-draft/ -- Nivel 1, is_active=False forzado."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'error': 'name requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        brand = BrandCommands.create_brand(name=name, is_active=False)
        _log_ai_action(request, 'CatalogBrandCreateDraftTool', {'brand_uuid': str(brand.uuid), 'name': name})
        return Response(_serialize_brand(brand), status=http_status.HTTP_201_CREATED)


class AiCatalogBrandUpdateView(APIView):
    """POST /api/v1/internal/ai/catalog/brands/update/ -- Nivel 2, solo name (logo/is_active excluidos)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            brand = BrandSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Marca no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
        data = {}
        if 'name' in request.data:
            data['name'] = request.data['name']
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)
        updated = BrandCommands.update_brand(brand, data)
        _log_ai_action(request, 'CatalogBrandUpdateTool', {'brand_uuid': str(updated.uuid), 'fields': list(data.keys())})
        return Response(_serialize_brand(updated))


class AiCatalogBrandSetPublishedStateView(APIView):
    """POST /api/v1/internal/ai/catalog/brands/set-published-state/ -- Nivel 3, HITL."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        is_active = request.data.get('is_active')
        if not uuid or not isinstance(is_active, bool):
            return Response({'error': 'uuid e is_active (booleano) son requeridos.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            brand = BrandSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Marca no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
        updated = BrandCommands.update_brand(brand, {'is_active': is_active})
        _log_ai_action(request, 'CatalogBrandSetPublishedStateTool', {'brand_uuid': str(updated.uuid), 'is_active': is_active})
        return Response(_serialize_brand(updated))


# ─── Tax (Decision 3, Fase 1: sin borrador, update es Nivel 3 con is_active incluido) ──

def _serialize_tax(tax) -> dict:
    return {
        'uuid': str(tax.uuid), 'name': tax.name, 'tax_type': tax.tax_type,
        'value': str(tax.value), 'is_active': tax.is_active,
    }


class AiCatalogTaxListView(APIView):
    """GET /api/v1/internal/ai/catalog/taxes/ -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = TaxSelector.list_all().filter(is_deleted=False)
        taxes = list(qs[:50])
        return Response({'count': len(taxes), 'taxes': [_serialize_tax(t) for t in taxes]})


class AiCatalogTaxGetView(APIView):
    """GET /api/v1/internal/ai/catalog/taxes/get/?uuid=... -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            tax = TaxSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Impuesto no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_tax(tax))


class AiCatalogTaxCreateView(APIView):
    """
    POST /api/v1/internal/ai/catalog/taxes/create/ -- Nivel 2 DIRECTO (sin
    borrador -- Decision 3 del catalogo de Tools, Fase 1: un impuesto no
    tiene un estado intermedio razonable, existe con un valor correcto o no
    existe).
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        tax_type = request.data.get('tax_type')
        value = request.data.get('value')
        if not name or not tax_type or value in (None, ''):
            return Response({'error': 'name, tax_type y value son requeridos.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            tax = TaxCommands.create_tax(name=name, tax_type=tax_type, value=value, is_active=True)
        except (TypeError, ValueError) as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        _log_ai_action(request, 'CatalogTaxCreateTool', {'tax_uuid': str(tax.uuid), 'name': name, 'value': str(value)})
        return Response(_serialize_tax(tax), status=http_status.HTTP_201_CREATED)


class AiCatalogTaxUpdateView(APIView):
    """
    POST /api/v1/internal/ai/catalog/taxes/update/ -- Nivel 3 CON HITL (Decision
    3, Fase 1: cambiar el valor de un impuesto existente recalcula el precio
    final de TODO el catalogo asociado de forma retroactiva e inmediata --
    mismo criterio de blast-radius que set_published_state, aplicado aqui a
    un campo de negocio. `is_active` SI se acepta en esta misma llamada
    (a diferencia de Product/Category/Brand) porque para Tax no hay una Tool
    de "borrador" previa que lo distinga -- toda escritura sobre un Tax
    existente es de alto impacto por igual.
    """
    permission_classes = [IsAdminUser]

    _ALLOWED_FIELDS = {'name', 'tax_type', 'value', 'is_active'}

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            tax = TaxSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Impuesto no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        data = {k: v for k, v in request.data.items() if k in self._ALLOWED_FIELDS}
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            updated = TaxCommands.update_tax(tax, data)
        except (TypeError, ValueError) as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        _log_ai_action(request, 'CatalogTaxUpdateTool', {'tax_uuid': str(updated.uuid), 'fields': list(data.keys())})
        return Response(_serialize_tax(updated))
