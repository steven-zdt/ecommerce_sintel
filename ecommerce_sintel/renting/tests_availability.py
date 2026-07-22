from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase

from renting.models import (
    Equipment, EquipmentVariant, RentalPeriod, RentalRequest, RentingCategory, EquipmentBlock,
)
from renting.services.availability import AvailabilityEngine


class AvailabilityEngineTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.vendor = User.objects.create_user(email='vendor_avail@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Avail', slug='cat-avail-test')
        equipment = Equipment.objects.create(
            vendor=self.vendor, category=category, name='Equipo Avail', slug='equipo-avail-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='AVAIL-SKU-1',
            rental_price_per_day=Decimal('100000.00'),
            rental_price_per_hour=Decimal('20000.00'),
            stock=1,
        )

    def _make_period(self, start_date, end_date, status=RentalPeriod.STATUS_SCHEDULED,
                      rental_mode=RentalRequest.RENTAL_MODE_DAYS,
                      start_time=None, end_time=None, quantity=1):
        return RentalPeriod.objects.create(
            rental_request=self._dummy_request(start_date, end_date),
            equipment_variant=self.variant,
            start_date=start_date, end_date=end_date,
            start_time=start_time, end_time=end_time,
            rental_mode=rental_mode, quantity=quantity, status=status,
        )

    def _dummy_request(self, start_date, end_date):
        return RentalRequest.objects.create(
            user=self.vendor, equipment_variant=self.variant,
            status=RentalRequest.STATUS_PAID,
            start_date=start_date, end_date=end_date,
            contact_email=self.vendor.email,
        )

    # ── Modo dias ────────────────────────────────────────────────────────────

    def test_day_mode_overlap_blocks(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5))
        self.assertFalse(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 3), date(2026, 7, 7))
        )

    def test_day_mode_checkout_same_day_does_not_overlap(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5))
        self.assertTrue(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 5), date(2026, 7, 8))
        )

    def test_day_mode_no_overlap_far_apart(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5))
        self.assertTrue(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 10), date(2026, 7, 15))
        )

    def test_stock_exhausted_blocks_even_without_overlap_check(self):
        self.variant.stock = 0
        self.variant.save(update_fields=['stock'])
        self.assertFalse(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 20), date(2026, 7, 25))
        )

    # ── Modo horas ───────────────────────────────────────────────────────────

    def test_hour_mode_same_day_overlap_blocks(self):
        self._make_period(
            date(2026, 7, 10), date(2026, 7, 10),
            rental_mode=RentalRequest.RENTAL_MODE_HOURS,
            start_time=time(8, 0), end_time=time(10, 0),
        )
        self.assertFalse(
            AvailabilityEngine.is_available(
                self.variant.id, date(2026, 7, 10), date(2026, 7, 10),
                rental_mode=RentalRequest.RENTAL_MODE_HOURS,
                start_time=time(9, 0), end_time=time(11, 0),
            )
        )

    def test_hour_mode_same_day_adjacent_slots_do_not_overlap(self):
        self._make_period(
            date(2026, 7, 10), date(2026, 7, 10),
            rental_mode=RentalRequest.RENTAL_MODE_HOURS,
            start_time=time(8, 0), end_time=time(10, 0),
        )
        self.assertTrue(
            AvailabilityEngine.is_available(
                self.variant.id, date(2026, 7, 10), date(2026, 7, 10),
                rental_mode=RentalRequest.RENTAL_MODE_HOURS,
                start_time=time(10, 0), end_time=time(12, 0),
            )
        )

    def test_mixed_day_mode_period_blocks_hour_mode_request(self):
        self._make_period(date(2026, 7, 5), date(2026, 7, 10))
        self.assertFalse(
            AvailabilityEngine.is_available(
                self.variant.id, date(2026, 7, 7), date(2026, 7, 7),
                rental_mode=RentalRequest.RENTAL_MODE_HOURS,
                start_time=time(8, 0), end_time=time(10, 0),
            )
        )

    def test_exclude_period_id_ignores_itself(self):
        period = self._make_period(date(2026, 7, 1), date(2026, 7, 5))
        self.assertFalse(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 1), date(2026, 7, 5))
        )
        self.assertTrue(
            AvailabilityEngine.is_available(
                self.variant.id, date(2026, 7, 1), date(2026, 7, 5),
                exclude_period_id=period.id,
            )
        )

    # ── find_next_available_slot ────────────────────────────────────────────

    def test_find_next_available_slot_skips_occupied_range(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5))
        result = AvailabilityEngine.find_next_available_slot(
            self.variant.id, date(2026, 7, 1), duration_days=3,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['date'], date(2026, 7, 5))

    def test_find_next_available_slot_none_when_fully_booked(self):
        self.variant.stock = 0
        self.variant.save(update_fields=['stock'])
        result = AvailabilityEngine.find_next_available_slot(
            self.variant.id, date(2026, 7, 1), duration_days=1, search_horizon_days=5,
        )
        self.assertIsNone(result)

    # ── generate_schedule ────────────────────────────────────────────────────

    def test_generate_schedule_default_statuses_excludes_cancelled(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5), status=RentalPeriod.STATUS_CANCELLED)
        self._make_period(date(2026, 7, 10), date(2026, 7, 15), status=RentalPeriod.STATUS_SCHEDULED)
        schedule = AvailabilityEngine.generate_schedule(
            self.variant.id, date(2026, 7, 1), date(2026, 7, 20)
        )
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]['start_date'], date(2026, 7, 10))

    def test_generate_schedule_all_statuses_includes_cancelled_for_timeline(self):
        self._make_period(date(2026, 7, 1), date(2026, 7, 5), status=RentalPeriod.STATUS_CANCELLED)
        self._make_period(date(2026, 7, 10), date(2026, 7, 15), status=RentalPeriod.STATUS_SCHEDULED)
        schedule = AvailabilityEngine.generate_schedule(
            self.variant.id, date(2026, 7, 1), date(2026, 7, 20),
            statuses=[choice[0] for choice in RentalPeriod.STATUS_CHOICES],
        )
        self.assertEqual(len(schedule), 2)

    # ── EquipmentBlock ───────────────────────────────────────────────────────

    def _make_block(self, start_date, end_date, status=EquipmentBlock.STATUS_ACTIVE, quantity=1):
        return EquipmentBlock.objects.create(
            equipment_variant=self.variant,
            block_type=EquipmentBlock.TYPE_MAINTENANCE,
            start_date=start_date, end_date=end_date,
            quantity=quantity, status=status, reason='Mantenimiento preventivo',
        )

    def test_active_block_overlap_blocks_availability(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5))
        self.assertFalse(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 3), date(2026, 7, 7))
        )

    def test_active_block_no_overlap_does_not_block(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5))
        self.assertTrue(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 10), date(2026, 7, 15))
        )

    def test_released_block_does_not_block_availability(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5), status=EquipmentBlock.STATUS_RELEASED)
        self.assertTrue(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 3), date(2026, 7, 7))
        )

    def test_partial_quantity_block_combines_with_rental_period(self):
        self.variant.stock = 3
        self.variant.save(update_fields=['stock'])
        self._make_period(date(2026, 7, 1), date(2026, 7, 10), quantity=2)
        self._make_block(date(2026, 7, 3), date(2026, 7, 6), quantity=1)
        # 3 stock - 2 (period) - 1 (block) = 0 free
        self.assertFalse(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 4), date(2026, 7, 5))
        )
        self.variant.stock = 4
        self.variant.save(update_fields=['stock'])
        self.assertTrue(
            AvailabilityEngine.is_available(self.variant.id, date(2026, 7, 4), date(2026, 7, 5))
        )

    def test_generate_schedule_includes_active_block_as_blocked(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5))
        schedule = AvailabilityEngine.generate_schedule(
            self.variant.id, date(2026, 7, 1), date(2026, 7, 10)
        )
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]['status'], 'blocked')

    def test_generate_schedule_default_excludes_released_block(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5), status=EquipmentBlock.STATUS_RELEASED)
        schedule = AvailabilityEngine.generate_schedule(
            self.variant.id, date(2026, 7, 1), date(2026, 7, 10)
        )
        self.assertEqual(schedule, [])

    def test_generate_schedule_all_statuses_includes_released_block_for_timeline(self):
        self._make_block(date(2026, 7, 1), date(2026, 7, 5), status=EquipmentBlock.STATUS_RELEASED)
        schedule = AvailabilityEngine.generate_schedule(
            self.variant.id, date(2026, 7, 1), date(2026, 7, 10),
            statuses=[choice[0] for choice in RentalPeriod.STATUS_CHOICES],
        )
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]['status'], 'block_released')
