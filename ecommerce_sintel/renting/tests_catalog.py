"""
Tests del catalogo enriquecido de Equipment (2026-07-16): RentalIncludedItem,
RentalExcludedItem, RentalFeature, RentalSpecificationGroup/RentalSpecification,
RentalRequirement, RentalServiceIncluded, RentalOptionalService, RentalFAQ,
RentalVideo, RentalDocument, y la galeria extendida (EquipmentImage).
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from renting.models import (
    Equipment, EquipmentVariant, EquipmentImage, RentingCategory,
    RentalIncludedItem, RentalExcludedItem, RentalFeature,
    RentalSpecificationGroup, RentalSpecification, RentalRequirement,
    RentalServiceIncluded, RentalOptionalService, RentalFAQ,
    RentalVideo, RentalDocument, RentalRequest, EquipmentReview,
)
from renting.services import (
    RentalIncludedItemCommands, RentalFeatureCommands,
    RentalSpecificationGroupCommands, RentalSpecificationCommands,
    RentalFAQCommands, RentalVideoCommands, RentalDocumentCommands,
    EquipmentReviewCommands,
)
from renting.services.selectors import RentingSelector
from renting.api.serializers import EquipmentDetailSerializer

User = get_user_model()

# PNG 1x1 valido (necesario porque ImageField valida contenido real con Pillow).
_PNG_BYTES = bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010802000000'
    '907753de0000000c4944415478da6360000002000155a5ee0e000000004'
    '9454e44ae426082'
)


class RentalCatalogModelsTestCase(APITestCase):
    """Commands de servicio: create/update/delete/toggle/duplicate/reorder."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_catalog@example.com', password='testpass123')
        self.category = RentingCategory.objects.create(name='Cat Catalog', slug='cat-catalog-test')
        self.equipment = Equipment.objects.create(
            vendor=self.vendor, category=self.category, name='Equipo Catalogo', slug='equipo-catalogo-test',
        )
        EquipmentVariant.objects.create(
            equipment=self.equipment, sku='CATALOG-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def test_included_item_crud_toggle_duplicate_reorder(self):
        item1 = RentalIncludedItemCommands.create(self.equipment, title='Cable', icon='bi-plug')
        item2 = RentalIncludedItemCommands.create(self.equipment, title='Maletin')

        RentalIncludedItemCommands.update(item1, title='Cable de poder')
        item1.refresh_from_db()
        self.assertEqual(item1.title, 'Cable de poder')

        toggled = RentalIncludedItemCommands.toggle_active(item1)
        self.assertFalse(toggled.is_active)
        RentalIncludedItemCommands.toggle_active(item1)

        dup = RentalIncludedItemCommands.duplicate(item2)
        self.assertNotEqual(dup.uuid, item2.uuid)
        self.assertIn('copia', dup.title)

        RentalIncludedItemCommands.reorder(self.equipment.id, [str(item2.uuid), str(item1.uuid)])
        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(item2.position, 0)
        self.assertEqual(item1.position, 1)

        RentalIncludedItemCommands.delete(item2)
        self.assertTrue(RentalIncludedItem.objects.get(pk=item2.pk).is_deleted)
        # item1 + el duplicado de item2 (`dup`) siguen activos -- solo item2 se borro.
        self.assertEqual(
            RentalIncludedItem.objects.filter(equipment=self.equipment, is_deleted=False).count(), 2,
        )

    def test_specification_group_cascade_soft_delete(self):
        group = RentalSpecificationGroupCommands.create(self.equipment, name='Motor')
        spec = RentalSpecificationCommands.create(self.equipment, group, name='Cilindraje', value='2000cc')

        RentalSpecificationGroupCommands.delete(group)

        group.refresh_from_db()
        spec.refresh_from_db()
        self.assertTrue(group.is_deleted)
        self.assertTrue(spec.is_deleted, 'Borrar el grupo debe arrastrar (soft-delete) sus especificaciones')

    def test_specification_must_belong_to_equipment_group(self):
        other_category = RentingCategory.objects.create(name='Cat Otro', slug='cat-otro-test')
        other_equipment = Equipment.objects.create(
            vendor=self.vendor, category=other_category, name='Otro Equipo', slug='otro-equipo-test',
        )
        group = RentalSpecificationGroupCommands.create(other_equipment, name='Motor')

        with self.assertRaises(ValueError):
            RentalSpecificationCommands.create(self.equipment, group, name='Cilindraje', value='2000cc')

    def test_video_requires_matching_source_fields(self):
        with self.assertRaises(ValueError):
            RentalVideoCommands.create(self.equipment, source_type=RentalVideo.SOURCE_YOUTUBE, video_url='')
        with self.assertRaises(ValueError):
            RentalVideoCommands.create(self.equipment, source_type=RentalVideo.SOURCE_MP4, video_file=None)

        video = RentalVideoCommands.create(
            self.equipment, source_type=RentalVideo.SOURCE_YOUTUBE,
            video_url='https://www.youtube.com/watch?v=xyz789',
        )
        self.assertEqual(video.equipment_id, self.equipment.id)

    def test_document_rejects_disallowed_extension(self):
        bad_file = SimpleUploadedFile('malware.exe', b'MZ...', content_type='application/octet-stream')
        with self.assertRaises(Exception):
            RentalDocumentCommands.create(
                self.equipment, file=bad_file, title='Bad', document_type=RentalDocument.TYPE_OTRO,
            )

    def test_document_accepts_pdf_and_tracks_downloads(self):
        pdf_file = SimpleUploadedFile('manual.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        doc = RentalDocumentCommands.create(
            self.equipment, file=pdf_file, title='Manual', document_type=RentalDocument.TYPE_MANUAL,
        )
        self.assertEqual(doc.downloads, 0)
        RentalDocumentCommands.register_download(doc)
        doc.refresh_from_db()
        self.assertEqual(doc.downloads, 1)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class RentalCatalogPublicPayloadTestCase(APITestCase):
    """El detalle publico GET /renting/equipment/{uuid}/ trae todo el catalogo
    enriquecido, sin N+1, y filtra filas inactivas/borradas."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_payload@example.com', password='testpass123')
        self.category = RentingCategory.objects.create(name='Cat Payload', slug='cat-payload-test')
        self.equipment = Equipment.objects.create(
            vendor=self.vendor, category=self.category, name='Equipo Payload', slug='equipo-payload-test',
            is_active=True,
        )
        EquipmentVariant.objects.create(
            equipment=self.equipment, sku='PAYLOAD-SKU-1', rental_price_per_day=Decimal('50000.00'), stock=3,
        )

        self.visible_item = RentalIncludedItemCommands.create(self.equipment, title='Visible')
        self.hidden_item = RentalIncludedItemCommands.create(self.equipment, title='Oculto', is_active=False)
        RentalFeatureCommands.create(self.equipment, title='Potencia', value='20T')
        group = RentalSpecificationGroupCommands.create(self.equipment, name='Motor')
        RentalSpecificationCommands.create(self.equipment, group, name='Cilindraje', value='2000cc')
        RentalFAQCommands.create(self.equipment, question='Pregunta?', answer='Respuesta.')

        public_doc = SimpleUploadedFile('manual.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        RentalDocumentCommands.create(
            self.equipment, file=public_doc, title='Manual publico',
            document_type=RentalDocument.TYPE_MANUAL, is_public=True,
        )
        private_doc = SimpleUploadedFile('interno.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        RentalDocumentCommands.create(
            self.equipment, file=private_doc, title='Interno',
            document_type=RentalDocument.TYPE_OTRO, is_public=False,
        )

        EquipmentImage.objects.create(equipment=self.equipment, image=SimpleUploadedFile(
            'gallery.png', _PNG_BYTES, content_type='image/png',
        ), image_type=EquipmentImage.TYPE_GALLERY)

    def test_endpoint_returns_enriched_single_payload(self):
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        titles = [i['title'] for i in data['included_items']]
        self.assertIn('Visible', titles)
        self.assertNotIn('Oculto', titles, 'is_active=False no debe mostrarse al cliente')

        self.assertEqual(len(data['features']), 1)
        self.assertEqual(data['specification_groups'][0]['name'], 'Motor')
        self.assertEqual(data['specification_groups'][0]['specifications'][0]['value'], '2000cc')
        self.assertEqual(len(data['faqs']), 1)
        self.assertEqual(len(data['images']), 1)

        doc_titles = [d['title'] for d in data['documents']]
        self.assertIn('Manual publico', doc_titles)
        self.assertNotIn('Interno', doc_titles, 'is_public=False no debe exponerse al cliente')

    def test_reviews_field_hides_soft_deleted(self):
        active = EquipmentReview.objects.create(
            user=self.vendor, equipment=self.equipment, rating=5, comment='Excelente',
        )
        deleted = EquipmentReview.objects.create(
            user=User.objects.create_user(email='other_reviewer@example.com', password='testpass123'),
            equipment=self.equipment, rating=1, comment='Borrado', is_deleted=True,
        )
        response = self.client.get(f'/api/v1/renting/equipment/{self.equipment.uuid}/')
        uuids = [r['uuid'] for r in response.data['reviews']]
        self.assertIn(str(active.uuid), uuids)
        self.assertNotIn(str(deleted.uuid), uuids)

    def test_selector_prefetches_without_n_plus_1(self):
        """RentingSelector.get_by_uuid() debe resolver todo el catalogo en un
        numero constante de queries, sin uno adicional por relacion hija."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            equipment = RentingSelector.get_by_uuid(str(self.equipment.uuid))
            EquipmentDetailSerializer(equipment).data
        # Una query por relacion prefetcheada (variants/images/reviews/included_items/
        # excluded_items/features/specification_groups/specification_groups__specifications/
        # requirements/services_included/optional_services/faqs/videos/documents) + la
        # query principal del equipo -- fijo, no escala con la cantidad de filas.
        self.assertLess(len(ctx.captured_queries), 20)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class EquipmentReviewFlowTestCase(APITestCase):
    """Reseñas de equipo: solo quien alquilo y ya termino la renta puede calificar."""

    def setUp(self):
        self.user = User.objects.create_user(email='reviewer@example.com', password='testpass123')
        self.other_user = User.objects.create_user(email='no_rental_user@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Review', slug='cat-review-test')
        self.equipment = Equipment.objects.create(
            vendor=self.user, category=category, name='Equipo Review', slug='equipo-review-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment, sku='REVIEW-SKU-1', rental_price_per_day=Decimal('50000.00'), stock=1,
        )

    def _create_finished_rental(self, user):
        return RentalRequest.objects.create(
            user=user, equipment_variant=self.variant, status=RentalRequest.STATUS_FINISHED,
            contact_email=user.email,
        )

    def test_create_review_requires_finished_rental(self):
        with self.assertRaises(ValueError):
            EquipmentReviewCommands.create_review(
                user=self.other_user, equipment=self.equipment, rating=5, comment='Buenisimo',
            )

    def test_create_review_succeeds_after_finished_rental(self):
        self._create_finished_rental(self.user)
        review = EquipmentReviewCommands.create_review(
            user=self.user, equipment=self.equipment, rating=4, comment='Muy buen equipo',
        )
        self.assertEqual(review.rating, 4)
        self.assertEqual(EquipmentReview.objects.filter(equipment=self.equipment).count(), 1)

    def test_create_review_rejects_duplicate(self):
        self._create_finished_rental(self.user)
        EquipmentReviewCommands.create_review(
            user=self.user, equipment=self.equipment, rating=4, comment='Primera reseña',
        )
        with self.assertRaises(ValueError):
            EquipmentReviewCommands.create_review(
                user=self.user, equipment=self.equipment, rating=2, comment='Segunda reseña',
            )

    def test_review_endpoint_rejects_user_without_finished_rental(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            f'/api/v1/renting/equipment/{self.equipment.uuid}/review/',
            {'rating': 5, 'comment': 'Deberia fallar'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_endpoint_requires_authentication(self):
        response = self.client.post(
            f'/api/v1/renting/equipment/{self.equipment.uuid}/review/',
            {'rating': 5, 'comment': 'Anonimo'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_review_endpoint_full_flow(self):
        self._create_finished_rental(self.user)
        self.client.force_authenticate(user=self.user)
        create_response = self.client.post(
            f'/api/v1/renting/equipment/{self.equipment.uuid}/review/',
            {'rating': 5, 'comment': 'Excelente servicio'},
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(f'/api/v1/renting/equipment/{self.equipment.uuid}/reviews/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['rating'], 5)
