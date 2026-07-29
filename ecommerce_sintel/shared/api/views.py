"""
ViewSet para el endpoint unificado de detalle pública.

Disponible en: GET /api/v1/unified/detail/{module}/{uuid}/

Donde module in ["renting", "shop", "service"]
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.presenters import (
    RentingPublicDetailPresenter,
    ShopPublicDetailPresenter,
    ServicePublicDetailPresenter,
)
from shared.serializers import UnifiedPublicDetailDTOSerializer


class UnifiedPublicDetailViewSet(viewsets.ViewSet):
    """
    Endpoint unificado para páginas de detalle pública.

    GET /api/v1/unified/detail/{module}/{uuid}/
    - module: "renting" | "shop" | "service"
    - uuid: UUID del item

    Retorna UnifiedPublicDetailDTO para consumo de frontend.
    """

    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        """GET /api/v1/unified/detail/{module}/{uuid}/"""

        module = request.query_params.get('module', 'renting')
        uuid = pk

        if not uuid:
            return Response(
                {'detail': 'UUID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if module == 'renting':
                from renting.services.selectors import RentingSelector
                equipment = RentingSelector.get_by_uuid(uuid)
                presenter = RentingPublicDetailPresenter(equipment, user=request.user)

            elif module == 'shop':
                from shop.services import ProductSelector
                product = ProductSelector.get_by_uuid(uuid)
                presenter = ShopPublicDetailPresenter(product, user=request.user)

            elif module == 'service':
                from technical_services.services import ServiceSelector
                service = ServiceSelector.get_by_uuid(uuid)
                presenter = ServicePublicDetailPresenter(service, user=request.user)

            else:
                return Response(
                    {'detail': f'Unknown module: {module}. Valid: renting, shop, service'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            dto = presenter.present()
            serializer = UnifiedPublicDetailDTOSerializer(dto)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
