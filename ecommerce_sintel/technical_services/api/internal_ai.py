"""
Endpoint interno read-only para el AI Engine (Fase 2 AI Core).

ServiceOperationSelector NO filtra por dueno (gap #4 del plan) -- este
endpoint agrega el owner-check el mismo (filter(order__user=...) /
verificacion de order.user_id), exactamente como exige la tabla de Tools
de la Fase 2 (`[owner-check manual]`).
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import Http404
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.services.admin_orchestrators import ServiceAdminOrchestrator
from ecommerce.internal_ai_utils import log_ai_action as _log_ai_action
from orders.services.selectors import OrderSelector
from technical_services.services.operations import ServiceOperationSelector
from technical_services.services.selectors import ServiceCategorySelector, ServiceSelector
from users.api.permissions import IsAdminUser, IsAuthenticatedActiveUser

MAX_LIST_LIMIT = 20


def _operation_to_dict(operation) -> dict:
    technician = operation.technician
    return {
        'order_uuid': str(operation.order.uuid),
        'status': operation.status,
        'status_label': operation.get_status_display(),
        'scheduled_date': operation.scheduled_date.isoformat() if operation.scheduled_date else None,
        'scheduled_time': operation.scheduled_time.isoformat() if operation.scheduled_time else None,
        'technician': technician.get_full_name() if technician else None,
        'completed_at': operation.completed_at.isoformat() if operation.completed_at else None,
    }


class AiServiceStatusView(APIView):
    """
    GET /api/v1/internal/ai/services/              -> operaciones de servicio del usuario
    GET /api/v1/internal/ai/services/?order=<uuid> -> la operacion de esa orden
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        order_uuid = request.query_params.get('order', '').strip()
        if order_uuid:
            try:
                order = OrderSelector.get_by_uuid(order_uuid)
            except Exception:
                raise Http404('Orden no encontrada.')
            if order.user_id != request.user.id:
                raise Http404('Orden no encontrada.')
            operation = getattr(order, 'service_operation', None)
            if operation is None:
                return Response({'operation': None, 'detail': 'La orden no tiene servicio tecnico asociado.'})
            return Response({'operation': _operation_to_dict(operation)})

        limit = min(int(request.query_params.get('limit', 5)), MAX_LIST_LIMIT)
        operations = (
            ServiceOperationSelector.queryset()
            .filter(order__user=request.user)
            .order_by('-created_at')[:limit]
        )
        return Response({'operations': [_operation_to_dict(op) for op in operations]})


# =============================================================================
# Admin AI Assistant, vertical Servicios -- PLAN_SINTEL_ADMIN_ASISTENTE_RAG_
# FORMULARIOS_LOOP.md, Fase 1-3 (2026-09-23). Namespace /services/admin/*,
# DELIBERADAMENTE separado de /services/ de arriba (ese es de cara al
# CLIENTE -- estado de SU operacion de servicio, IsAuthenticatedActiveUser;
# esto es de cara al ADMIN -- CRUD del catalogo de servicios, IsAdminUser).
# Mismo patron exacto que shop/api/internal_ai.py (vertical Catalogo).
#
# Cubre Nivel 0-2 (lectura, borrador, edicion) unicamente -- mismo alcance
# deliberadamente acotado que Product en su primera fase. set_published_state
# (Nivel 3, HITL) y delete (Nivel 4) quedan para una fase posterior.
#
# Motivo real de esta vertical (no hipotetico): CatalogAgent solo tenia
# Tools de Product/Category/Brand/Tax -- al pedirle "crear un servicio",
# usaba su propia logica/instruccion de PRODUCTO (pregunto marca/condicion,
# campos que TechnicalService ni siquiera tiene) porque no existia ninguna
# Tool real de Servicios que pudiera usar en su lugar.
# =============================================================================


def _serialize_service(service) -> dict:
    default_variant = next((v for v in service.variants.all() if v.is_default and not v.is_deleted), None)
    return {
        'uuid': str(service.uuid),
        'name': service.name,
        'slug': service.slug,
        'is_active': service.is_active,
        'is_featured': service.is_featured,
        'description': service.description,
        'scope': service.scope,
        'warranty': service.warranty,
        'coverage_notes': service.coverage_notes,
        'category': (
            {'uuid': str(service.category.uuid), 'name': service.category.name}
            if service.category_id else None
        ),
        'level': (
            {'uuid': str(service.level.uuid), 'name': service.level.name}
            if service.level_id else None
        ),
        'default_variant': (
            {
                'uuid': str(default_variant.uuid),
                'pricing_strategy': default_variant.pricing_strategy,
                'fixed_price': str(default_variant.fixed_price) if default_variant.fixed_price is not None else None,
                'estimated_hours': str(default_variant.estimated_hours),
            }
            if default_variant else None
        ),
        'meta_title': service.meta_title,
        'meta_description': service.meta_description,
    }


def _serialize_service_category(category) -> dict:
    return {'uuid': str(category.uuid), 'name': category.name}


def _parse_price(raw):
    """
    Bug real encontrado en vivo (2026-09-23, primer smoke test del caso de
    aceptacion "crear servicio... por 1500000 pesos"): el LLM mando `price`
    como un dict (`{'amount': 1500000, 'currency': 'COP', ...}`) en vez de
    un numero simple -- el Tool schema declara `price` como number, pero
    nunca hay que confiar en que el LLM respete el tipo declarado. Sin este
    parseo, `TechnicalService.objects.create()` fallaba con un
    `TypeError`/`ValidationError` sin capturar -> 500 crudo con traceback
    completo expuesto al bridge de Tools.

    Devuelve un Decimal valido o None (nunca lanza) -- el caller decide el
    400 limpio. Acepta int/float/str numerica, y como defensa adicional
    intenta extraer 'amount'/'price'/'value' si llega un dict (honra la
    intencion real del LLM en vez de solo rechazarlo).
    """
    if isinstance(raw, dict):
        raw = raw.get('amount', raw.get('price', raw.get('value')))
    if raw in (None, ''):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None


class AiServiceAdminListView(APIView):
    """GET /api/v1/internal/ai/services/admin/ -- lectura, sin auditoria (Nivel 0)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ServiceSelector.list_all_for_admin()
        search = request.query_params.get('search')
        is_active = request.query_params.get('is_active')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if is_active in ('true', 'false'):
            qs = qs.filter(is_active=is_active == 'true')
        try:
            limit = min(int(request.query_params.get('limit', 20)), 50)
        except (TypeError, ValueError):
            limit = 20
        services = list(qs[:limit])
        return Response({'count': len(services), 'services': [_serialize_service(s) for s in services]})


class AiServiceAdminGetView(APIView):
    """GET /api/v1/internal/ai/services/admin/get/?uuid=... -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            service = ServiceSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Servicio no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_service(service))


class AiServiceAdminCreateDraftView(APIView):
    """
    POST /api/v1/internal/ai/services/admin/create-draft/ -- Nivel 1 (borrador).

    Regla dura (mismo criterio que Product Decision 1): un servicio creado
    por esta via SIEMPRE nace is_active=False, sin importar lo que pida el
    payload -- publicar es una Tool separada (Nivel 3, HITL, no implementada
    todavia).

    Precio: TechnicalService NO tiene un campo `price` propio (a diferencia
    de Product) -- el precio real vive en la variante por defecto
    (ServiceVariant.fixed_price/estimated_hours, ver ServicePricingCalculator).
    Esta vista SIEMPRE crea la variante por defecto en la misma transaccion
    (ServiceAdminOrchestrator.create_service_with_default_variant, ya
    atomica) -- un servicio nunca queda sin variante por defecto, igual que
    un Product nunca queda sin su ProductVariant por defecto.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        data = request.data
        name = (data.get('name') or '').strip()
        price = _parse_price(data.get('price'))
        if not name or price is None:
            return Response(
                {'error': 'name y price (numero valido) son requeridos.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        category = None
        category_uuid = data.get('category')
        if category_uuid:
            try:
                category = ServiceCategorySelector.get_by_uuid(category_uuid)
            except Http404:
                return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            service = ServiceAdminOrchestrator.create_service_with_default_variant(
                vendor=request.user,
                service_data={
                    'name': name,
                    'description': data.get('description', ''),
                    'scope': data.get('scope', ''),
                    'warranty': data.get('warranty', ''),
                    'coverage_notes': data.get('coverage_notes', ''),
                    'category': category,
                    'is_active': False,  # SIEMPRE -- ver docstring de la clase.
                    'is_featured': bool(data.get('is_featured', False)),
                },
                variant_data={
                    # pricing_strategy=FIXED: el caso real de esta Fase 1-3 es
                    # "crear servicio X por N pesos" (precio unico, no por
                    # hora) -- HOURLY con estimated_hours/complexity_factor
                    # queda para cuando el admin lo pida explicito, no se
                    # inventa un calculo por horas de un precio que el
                    # usuario dio como total.
                    'pricing_strategy': 'FIXED',
                    'fixed_price': price,
                },
            )
        except (TypeError, ValueError, DjangoValidationError) as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)

        service = ServiceSelector.get_by_uuid(service.uuid)
        _log_ai_action(request, 'ServiceCreateDraftTool', {'service_uuid': str(service.uuid), 'name': name})
        return Response(_serialize_service(service), status=http_status.HTTP_201_CREATED)


class AiServiceAdminUpdateDraftView(APIView):
    """
    POST /api/v1/internal/ai/services/admin/update-draft/ -- Nivel 2 (mutacion auditada).

    Edita contenido/categoria de un servicio YA EXISTENTE. NUNCA acepta
    `is_active` -- publicar/despublicar queda para una Tool separada (Nivel
    3, HITL, no implementada todavia), descartado aqui como segunda capa de
    defensa (la primera es que el Tool schema del lado del LLM ni siquiera
    declara ese campo).
    """
    permission_classes = [IsAdminUser]

    _ALLOWED_FIELDS = {'name', 'description', 'scope', 'warranty', 'coverage_notes', 'is_featured'}

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            service = ServiceSelector.get_by_uuid(uuid)
        except Http404:
            return Response({'error': 'Servicio no encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        data = {k: v for k, v in request.data.items() if k in self._ALLOWED_FIELDS}

        category_uuid = request.data.get('category')
        if category_uuid:
            try:
                data['category'] = ServiceCategorySelector.get_by_uuid(category_uuid)
            except Http404:
                return Response({'error': 'Categoria no encontrada.'}, status=http_status.HTTP_400_BAD_REQUEST)

        raw_price = request.data.get('price')
        if raw_price not in (None, ''):
            price = _parse_price(raw_price)
            if price is None:
                return Response({'error': 'price debe ser un numero valido.'}, status=http_status.HTTP_400_BAD_REQUEST)
            default_variant = next((v for v in service.variants.all() if v.is_default and not v.is_deleted), None)
            if default_variant is not None:
                default_variant.fixed_price = price
                default_variant.save(update_fields=['fixed_price'])

        if data:
            service = ServiceAdminOrchestrator.update_service(service, data)
        service = ServiceSelector.get_by_uuid(service.uuid)
        _log_ai_action(request, 'ServiceUpdateDraftTool', {'service_uuid': str(service.uuid)})
        return Response(_serialize_service(service))


class AiServiceAdminCategoryListView(APIView):
    """GET /api/v1/internal/ai/services/admin/categories/ -- Nivel 0."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ServiceCategorySelector.list_all_for_admin()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search))
        try:
            limit = min(int(request.query_params.get('limit', 20)), 50)
        except (TypeError, ValueError):
            limit = 20
        categories = list(qs[:limit])
        return Response({'count': len(categories), 'categories': [_serialize_service_category(c) for c in categories]})
