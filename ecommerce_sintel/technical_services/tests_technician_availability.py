from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import TechnicianProfile, UserProfile
from orders.models import Order, OrderItem
from technical_services.models import (
    ServiceCategory, ServiceLevel, ServiceOperation, TechnicalService, ServiceVariant,
    OrderServiceDetail, WorkingSchedule, WorkingException,
)
from technical_services.services.technician_availability import TechnicianAvailabilityEngine
from technical_services.services.commands import WorkingScheduleCommands, WorkingExceptionCommands, ServiceCommands
from technical_services.services.operations import ServiceOperationCommands
from technical_services.services.calendar import build_calendar_feed

User = get_user_model()

# 2026-07-13 es lunes -- fecha fija para que weekday() sea predecible en los tests.
MONDAY = date(2026, 7, 13)


class TechnicianAvailabilityEngineTestCase(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(email='tech_avail@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=WorkingSchedule.MONDAY,
            start_time=time(7, 0), end_time=time(18, 0),
        )

    def _make_operation(self, scheduled_time, duration_minutes=60, status=ServiceOperation.TECHNICIAN_ASSIGNED, scheduled_date=MONDAY):
        order = Order.objects.create(user=self.technician, total_amount=Decimal('0'))
        return ServiceOperation.objects.create(
            order=order, technician=self.technician, status=status,
            scheduled_date=scheduled_date, scheduled_time=scheduled_time,
            estimated_duration_minutes=duration_minutes,
        )

    # ── get_working_window ──────────────────────────────────────────────────

    def test_get_working_window_returns_schedule_for_that_weekday(self):
        start, end = TechnicianAvailabilityEngine.get_working_window(self.technician.id, MONDAY)
        self.assertEqual((start, end), (time(7, 0), time(18, 0)))

    def test_get_working_window_none_when_technician_does_not_work_that_day(self):
        sunday = MONDAY + timedelta(days=6)
        start, end = TechnicianAvailabilityEngine.get_working_window(self.technician.id, sunday)
        self.assertIsNone(start)
        self.assertIsNone(end)

    # ── free_windows ─────────────────────────────────────────────────────────

    def test_free_windows_full_day_when_no_exceptions_or_slots(self):
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(18, 0))])

    def test_free_windows_empty_with_full_day_exception(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_VACATION,
            start_date=MONDAY, end_date=MONDAY,
        )
        self.assertEqual(TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY), [])

    def test_free_windows_subtracts_partial_exception(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_PERMIT,
            start_date=MONDAY, end_date=MONDAY,
            start_time=time(9, 0), end_time=time(11, 0),
        )
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(9, 0)), (time(11, 0), time(18, 0))])

    def test_free_windows_subtracts_confirmed_operation(self):
        self._make_operation(scheduled_time=time(10, 0), duration_minutes=120)
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(10, 0)), (time(12, 0), time(18, 0))])

    def test_free_windows_ignores_cancelled_operation(self):
        self._make_operation(scheduled_time=time(10, 0), status=ServiceOperation.CANCELLED)
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(18, 0))])

    def test_free_windows_counts_completed_operation(self):
        self._make_operation(scheduled_time=time(10, 0), status=ServiceOperation.COMPLETED)
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(10, 0)), (time(11, 0), time(18, 0))])

    # ── EXTRA_HOURS (Fase 6) ─────────────────────────────────────────────────

    def test_free_windows_adds_extra_hours_to_normal_schedule(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=MONDAY, end_date=MONDAY, start_time=time(18, 0), end_time=time(20, 0),
        )
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY)
        self.assertEqual(windows, [(time(7, 0), time(18, 0)), (time(18, 0), time(20, 0))])

    def test_free_windows_extra_hours_works_on_day_without_schedule(self):
        sunday = MONDAY + timedelta(days=6)
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=sunday, end_date=sunday, start_time=time(9, 0), end_time=time(13, 0),
        )
        windows = TechnicianAvailabilityEngine.free_windows(self.technician.id, sunday)
        self.assertEqual(windows, [(time(9, 0), time(13, 0))])

    def test_free_windows_full_day_exception_cancels_extra_hours_too(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=MONDAY, end_date=MONDAY, start_time=time(18, 0), end_time=time(20, 0),
        )
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_VACATION,
            start_date=MONDAY, end_date=MONDAY,
        )
        self.assertEqual(TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY), [])

    def test_is_available_true_within_extra_hours_window(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=MONDAY, end_date=MONDAY, start_time=time(18, 0), end_time=time(20, 0),
        )
        self.assertTrue(
            TechnicianAvailabilityEngine.is_available(self.technician.id, MONDAY, time(18, 30), time(19, 30))
        )

    def test_capacity_summary_includes_extra_hours_in_capacity_and_free(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=MONDAY, end_date=MONDAY, start_time=time(18, 0), end_time=time(20, 0),
        )
        summary = TechnicianAvailabilityEngine.capacity_summary(MONDAY)
        self.assertEqual(summary['capacity_hours'], Decimal('13'))  # 11h normal + 2h extra
        self.assertEqual(summary['free_hours'], Decimal('13'))
        self.assertEqual(summary['occupied_hours'], Decimal('0'))

    def test_capacity_summary_counts_technician_with_only_extra_hours(self):
        sunday = MONDAY + timedelta(days=6)
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_EXTRA_HOURS,
            start_date=sunday, end_date=sunday, start_time=time(9, 0), end_time=time(13, 0),
        )
        summary = TechnicianAvailabilityEngine.capacity_summary(sunday)
        self.assertEqual(summary['technicians_total'], 1)
        self.assertEqual(summary['capacity_hours'], Decimal('4'))

    # ── is_available ─────────────────────────────────────────────────────────

    def test_is_available_true_when_range_fits_free_window(self):
        self.assertTrue(
            TechnicianAvailabilityEngine.is_available(self.technician.id, MONDAY, time(8, 0), time(9, 0))
        )

    def test_is_available_false_when_range_overlaps_confirmed_operation(self):
        self._make_operation(scheduled_time=time(8, 0), duration_minutes=60)
        self.assertFalse(
            TechnicianAvailabilityEngine.is_available(self.technician.id, MONDAY, time(8, 0), time(9, 0))
        )

    def test_is_available_false_outside_working_hours(self):
        self.assertFalse(
            TechnicianAvailabilityEngine.is_available(self.technician.id, MONDAY, time(18, 0), time(19, 0))
        )

    # ── occupied_hours / capacity_summary ───────────────────────────────────

    def test_occupied_hours_sums_confirmed_operations_only(self):
        self._make_operation(scheduled_time=time(8, 0), duration_minutes=60)
        self._make_operation(scheduled_time=time(10, 0), duration_minutes=90)
        self._make_operation(scheduled_time=time(14, 0), status=ServiceOperation.CANCELLED)
        self.assertEqual(
            TechnicianAvailabilityEngine.occupied_hours(self.technician.id, MONDAY), Decimal('2.5'),
        )

    def test_capacity_summary_matches_spec_example(self):
        techs = [self.technician]
        for i in range(4):
            tech = User.objects.create_user(email=f'tech_capacity_{i}@example.com', password='testpass123')
            TechnicianProfile.objects.create(user=tech)
            WorkingSchedule.objects.create(
                technician=tech, weekday=WorkingSchedule.MONDAY,
                start_time=time(7, 0), end_time=time(18, 0),
            )
            techs.append(tech)

        # 5 tecnicos x 11h = 55h de capacidad; 4h confirmadas sobre el primero.
        self._make_operation(scheduled_time=time(8, 0), duration_minutes=240)

        summary = TechnicianAvailabilityEngine.capacity_summary(MONDAY)
        self.assertEqual(summary['technicians_total'], 5)
        self.assertEqual(summary['capacity_hours'], Decimal('55'))
        self.assertEqual(summary['occupied_hours'], Decimal('4'))
        self.assertEqual(summary['free_hours'], Decimal('51'))
        self.assertEqual(summary['technicians_available'], 5)

    def test_capacity_summary_excludes_technicians_without_schedule_that_day(self):
        sunday = MONDAY + timedelta(days=6)
        summary = TechnicianAvailabilityEngine.capacity_summary(sunday)
        self.assertEqual(summary['technicians_total'], 0)

    # ── list_available_technicians ──────────────────────────────────────────

    def test_list_available_technicians_never_includes_fully_booked_technician(self):
        self._make_operation(scheduled_time=time(7, 0), duration_minutes=660)  # 07:00-18:00 completo
        results = TechnicianAvailabilityEngine.list_available_technicians(MONDAY, time(8, 0), time(9, 0))
        self.assertEqual(results, [])

    def test_list_available_technicians_includes_free_technician_with_windows(self):
        results = TechnicianAvailabilityEngine.list_available_technicians(MONDAY, time(8, 0), time(9, 0))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['technician_id'], self.technician.id)
        self.assertEqual(results[0]['free_windows'], [(time(7, 0), time(18, 0))])

    def test_list_available_technicians_filters_by_category(self):
        category = ServiceCategory.objects.create(name='Cat Avail Engine', slug='cat-avail-engine-test')
        self.technician.technician_profile.specialties.add(category)
        other_category = ServiceCategory.objects.create(name='Other Cat', slug='other-cat-test')

        matching = TechnicianAvailabilityEngine.list_available_technicians(MONDAY, time(8, 0), time(9, 0), category)
        self.assertEqual(len(matching), 1)

        non_matching = TechnicianAvailabilityEngine.list_available_technicians(MONDAY, time(8, 0), time(9, 0), other_category)
        self.assertEqual(non_matching, [])

    # ── capacity_summary_range (Fase 3) ─────────────────────────────────────

    def test_capacity_summary_range_sums_across_week(self):
        # El tecnico solo tiene horario los lunes -- una semana completa (lun-dom)
        # debe sumar 11h de capacidad total (un solo dia habil) y el resto en 0.
        sunday = MONDAY + timedelta(days=6)
        result = TechnicianAvailabilityEngine.capacity_summary_range(MONDAY, sunday)
        self.assertEqual(len(result['days']), 7)
        self.assertEqual(result['totals']['capacity_hours'], Decimal('11'))
        self.assertEqual(result['totals']['free_hours'], Decimal('11'))
        self.assertEqual(result['totals']['occupied_hours'], Decimal('0'))

    def test_capacity_summary_range_includes_occupied_hours_from_confirmed_operation(self):
        self._make_operation(scheduled_time=time(8, 0), duration_minutes=180)
        result = TechnicianAvailabilityEngine.capacity_summary_range(MONDAY, MONDAY)
        self.assertEqual(result['totals']['occupied_hours'], Decimal('3'))
        self.assertEqual(result['days'][0]['date'], MONDAY)

    def test_capacity_summary_range_rejects_end_before_start(self):
        with self.assertRaises(ValueError):
            TechnicianAvailabilityEngine.capacity_summary_range(MONDAY, MONDAY - timedelta(days=1))

    def test_capacity_summary_range_rejects_range_too_large(self):
        with self.assertRaises(ValueError):
            TechnicianAvailabilityEngine.capacity_summary_range(MONDAY, MONDAY + timedelta(days=93))

    # ── find_next_available_technician (Fase 7) ─────────────────────────────

    def test_find_next_available_technician_same_day(self):
        result = TechnicianAvailabilityEngine.find_next_available_technician(MONDAY, duration_minutes=60)
        self.assertIsNotNone(result)
        self.assertEqual(result['technician_id'], self.technician.id)
        self.assertEqual(result['date'], MONDAY)
        self.assertEqual(result['start_time'], time(7, 0))
        self.assertEqual(result['end_time'], time(8, 0))

    def test_find_next_available_technician_prefers_preferred_time_when_it_fits(self):
        result = TechnicianAvailabilityEngine.find_next_available_technician(
            MONDAY, duration_minutes=60, preferred_time=time(10, 0),
        )
        self.assertEqual(result['start_time'], time(10, 0))
        self.assertEqual(result['end_time'], time(11, 0))

    def test_find_next_available_technician_skips_to_next_day_when_full(self):
        self._make_operation(scheduled_time=time(7, 0), duration_minutes=11 * 60)  # todo el lunes ocupado
        tuesday = MONDAY + timedelta(days=1)
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=tuesday.weekday(),
            start_time=time(7, 0), end_time=time(18, 0),
        )
        result = TechnicianAvailabilityEngine.find_next_available_technician(MONDAY, duration_minutes=60)
        self.assertEqual(result['date'], tuesday)

    def test_find_next_available_technician_none_within_horizon(self):
        result = TechnicianAvailabilityEngine.find_next_available_technician(
            MONDAY, duration_minutes=60,
            category=ServiceCategory.objects.create(name='Cat Sin Nadie', slug='cat-sin-nadie-test'),
        )
        self.assertIsNone(result)


class WorkingScheduleCommandsTestCase(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(email='wsc_tech@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)

    def test_upsert_schedule_creates_and_updates(self):
        schedule = WorkingScheduleCommands.upsert_schedule(
            self.technician, WorkingSchedule.MONDAY, time(7, 0), time(16, 0),
        )
        self.assertEqual(schedule.end_time, time(16, 0))

        updated = WorkingScheduleCommands.upsert_schedule(
            self.technician, WorkingSchedule.MONDAY, time(8, 0), time(17, 0),
        )
        self.assertEqual(updated.id, schedule.id)
        self.assertEqual(updated.end_time, time(17, 0))
        self.assertEqual(WorkingSchedule.objects.filter(technician=self.technician).count(), 1)

    def test_upsert_schedule_rejects_end_before_start(self):
        with self.assertRaises(ValueError):
            WorkingScheduleCommands.upsert_schedule(self.technician, WorkingSchedule.MONDAY, time(16, 0), time(7, 0))

    def test_delete_schedule_soft_deletes_and_engine_ignores_it(self):
        schedule = WorkingScheduleCommands.upsert_schedule(
            self.technician, WorkingSchedule.MONDAY, time(7, 0), time(18, 0),
        )
        WorkingScheduleCommands.delete_schedule(schedule)
        schedule.refresh_from_db()
        self.assertTrue(schedule.is_deleted)
        start, _ = TechnicianAvailabilityEngine.get_working_window(self.technician.id, MONDAY)
        self.assertIsNone(start)


class WorkingExceptionCommandsTestCase(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(email='wec_tech@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)

    def test_create_exception_rejects_end_before_start_date(self):
        with self.assertRaises(ValueError):
            WorkingExceptionCommands.create_exception(
                self.technician, WorkingException.TYPE_VACATION,
                start_date=MONDAY, end_date=MONDAY - timedelta(days=1),
            )

    def test_create_exception_rejects_mismatched_times(self):
        with self.assertRaises(ValueError):
            WorkingExceptionCommands.create_exception(
                self.technician, WorkingException.TYPE_PERMIT,
                start_date=MONDAY, end_date=MONDAY, start_time=time(9, 0), end_time=None,
            )

    def test_create_exception_rejects_full_day_extra_hours(self):
        with self.assertRaises(ValueError):
            WorkingExceptionCommands.create_exception(
                self.technician, WorkingException.TYPE_EXTRA_HOURS,
                start_date=MONDAY, end_date=MONDAY,
            )

    def test_create_exception_accepts_extra_hours_with_times(self):
        exc = WorkingExceptionCommands.create_exception(
            self.technician, WorkingException.TYPE_EXTRA_HOURS,
            start_date=MONDAY, end_date=MONDAY, start_time=time(18, 0), end_time=time(20, 0),
        )
        self.assertEqual(exc.exception_type, WorkingException.TYPE_EXTRA_HOURS)

    def test_delete_exception_soft_deletes_and_engine_ignores_it(self):
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=WorkingSchedule.MONDAY,
            start_time=time(7, 0), end_time=time(18, 0),
        )
        exception = WorkingExceptionCommands.create_exception(
            self.technician, WorkingException.TYPE_VACATION, start_date=MONDAY, end_date=MONDAY,
        )
        self.assertEqual(TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY), [])

        WorkingExceptionCommands.delete_exception(exception)
        self.assertEqual(
            TechnicianAvailabilityEngine.free_windows(self.technician.id, MONDAY),
            [(time(7, 0), time(18, 0))],
        )


class TechnicianAvailabilityEndpointsTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='avail_endpoint_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.non_admin = User.objects.create_user(email='avail_endpoint_customer@example.com', password='testpass123')
        self.technician = User.objects.create_user(email='avail_endpoint_tech@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=WorkingSchedule.MONDAY,
            start_time=time(7, 0), end_time=time(18, 0),
        )

    def test_non_admin_cannot_query_availability(self):
        self.client.force_authenticate(user=self.non_admin)
        response = self.client.get('/api/v1/services/technician-availability/', {
            'date': MONDAY.isoformat(), 'start_time': '08:00', 'end_time': '09:00',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_queries_available_technicians(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/services/technician-availability/', {
            'date': MONDAY.isoformat(), 'start_time': '08:00', 'end_time': '09:00',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['technician_id'], self.technician.id)

    def test_admin_queries_capacity_summary(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/services/technician-availability/summary/', {
            'date': MONDAY.isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['technicians_total'], 1)
        self.assertEqual(Decimal(response.data['capacity_hours']), Decimal('11.00'))

    def test_admin_queries_range_summary(self):
        self.client.force_authenticate(user=self.admin)
        sunday = MONDAY + timedelta(days=6)
        response = self.client.get('/api/v1/services/technician-availability/range-summary/', {
            'start_date': MONDAY.isoformat(), 'end_date': sunday.isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['days']), 7)
        self.assertEqual(Decimal(response.data['totals']['capacity_hours']), Decimal('11.00'))

    def test_range_summary_rejects_range_too_large(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/services/technician-availability/range-summary/', {
            'start_date': MONDAY.isoformat(), 'end_date': (MONDAY + timedelta(days=200)).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_creates_and_lists_working_schedule(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/v1/services/working-schedules/', {
            'technician': str(self.technician.uuid),
            'weekday': WorkingSchedule.TUESDAY,
            'start_time': '08:00', 'end_time': '17:00',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        listing = self.client.get('/api/v1/services/working-schedules/', {'technician': str(self.technician.uuid)})
        self.assertEqual(listing.data['count'], 2)

    def test_admin_creates_working_exception(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/v1/services/working-exceptions/', {
            'technician': str(self.technician.uuid),
            'exception_type': WorkingException.TYPE_VACATION,
            'start_date': MONDAY.isoformat(), 'end_date': MONDAY.isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['exception_type'] == WorkingException.TYPE_VACATION)

        availability = self.client.get('/api/v1/services/technician-availability/', {
            'date': MONDAY.isoformat(), 'start_time': '08:00', 'end_time': '09:00',
        })
        self.assertEqual(availability.data, [])

    def test_admin_queries_calendar_feed(self):
        self.client.force_authenticate(user=self.admin)
        sunday = MONDAY + timedelta(days=6)
        response = self.client.get('/api/v1/services/technician-availability/calendar/', {
            'start_date': MONDAY.isoformat(), 'end_date': sunday.isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['technicians']), 1)
        self.assertEqual(len(response.data['technicians'][0]['days']), 7)
        monday_entry = response.data['technicians'][0]['days'][0]
        self.assertEqual(monday_entry['working_window']['start'], '07:00:00')

    def test_calendar_rejects_range_too_large(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/services/technician-availability/calendar/', {
            'start_date': MONDAY.isoformat(), 'end_date': (MONDAY + timedelta(days=40)).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CalendarFeedTestCase(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(email='calendar_tech@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=WorkingSchedule.MONDAY,
            start_time=time(7, 0), end_time=time(18, 0),
        )
        self.customer = User.objects.create_user(email='calendar_customer@example.com', password='testpass123')

    def test_feed_includes_working_window_and_operation_block(self):
        order = Order.objects.create(user=self.customer, total_amount=Decimal('0'))
        ServiceOperation.objects.create(
            order=order, technician=self.technician, status=ServiceOperation.TECHNICIAN_ASSIGNED,
            scheduled_date=MONDAY, scheduled_time=time(9, 0), estimated_duration_minutes=90,
        )

        feed = build_calendar_feed([self.technician], MONDAY, MONDAY)
        tech_entry = feed['technicians'][0]
        self.assertEqual(tech_entry['technician_id'], self.technician.id)
        day = tech_entry['days'][0]
        self.assertEqual(day['working_window'], {'start': time(7, 0), 'end': time(18, 0)})
        self.assertEqual(len(day['operations']), 1)
        self.assertEqual(day['operations'][0]['start_time'], time(9, 0))
        self.assertEqual(day['operations'][0]['end_time'], time(10, 30))
        self.assertTrue(day['operations'][0]['customer_name'])  # nombre o email, nunca vacio

    def test_feed_excludes_cancelled_operations(self):
        order = Order.objects.create(user=self.customer, total_amount=Decimal('0'))
        ServiceOperation.objects.create(
            order=order, technician=self.technician, status=ServiceOperation.CANCELLED,
            scheduled_date=MONDAY, scheduled_time=time(9, 0), estimated_duration_minutes=60,
        )
        feed = build_calendar_feed([self.technician], MONDAY, MONDAY)
        self.assertEqual(feed['technicians'][0]['days'][0]['operations'], [])

    def test_feed_includes_exceptions(self):
        WorkingException.objects.create(
            technician=self.technician, exception_type=WorkingException.TYPE_VACATION,
            start_date=MONDAY, end_date=MONDAY,
        )
        feed = build_calendar_feed([self.technician], MONDAY, MONDAY)
        exceptions = feed['technicians'][0]['days'][0]['exceptions']
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]['exception_type'], WorkingException.TYPE_VACATION)

    def test_feed_working_window_none_when_no_schedule_that_day(self):
        sunday = MONDAY + timedelta(days=6)
        feed = build_calendar_feed([self.technician], sunday, sunday)
        self.assertIsNone(feed['technicians'][0]['days'][0]['working_window'])

    def test_feed_rejects_range_too_large(self):
        with self.assertRaises(ValueError):
            build_calendar_feed([self.technician], MONDAY, MONDAY + timedelta(days=32))

    def test_feed_rejects_end_before_start(self):
        with self.assertRaises(ValueError):
            build_calendar_feed([self.technician], MONDAY, MONDAY - timedelta(days=1))


class AutoAssignViaEngineTestCase(APITestCase):
    """Fase 7: auto-asignacion real via TechnicianAvailabilityEngine."""

    def setUp(self):
        self.customer = User.objects.create_user(email='auto_assign_customer@example.com', password='testpass123')
        self.admin = User.objects.create_user(
            email='auto_assign_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.technician = User.objects.create_user(email='auto_assign_tech@example.com', password='testpass123')
        TechnicianProfile.objects.create(user=self.technician)
        UserProfile.objects.create(
            user=self.technician, first_name='Auto', last_name='Assign', user_type='TECHNICIAN',
        )
        WorkingSchedule.objects.create(
            technician=self.technician, weekday=MONDAY.weekday(),
            start_time=time(7, 0), end_time=time(18, 0),
        )

        category = ServiceCategory.objects.create(name='Cat Auto Assign', slug='cat-auto-assign-test')
        level = ServiceLevel.objects.create(name='Nivel Auto Assign', slug='nivel-auto-assign-test')
        service = TechnicalService.objects.create(
            vendor=self.admin, category=category, level=level,
            name='Servicio Auto Assign', slug='servicio-auto-assign-test',
        )
        self.variant = ServiceVariant.objects.create(
            service=service, sku='AUTO-ASSIGN-SKU-1', estimated_hours=Decimal('1.00'),
            pricing_strategy=ServiceVariant.FIXED, fixed_price=Decimal('100000.00'),
        )
        # get_active_technicians_for_category() filtra por specialties -- sin esto
        # el motor nunca encuentra al tecnico de prueba para esta categoria.
        self.technician.technician_profile.specialties.add(category)

    def _make_order_with_operation(self, preferred_date=MONDAY, preferred_time=None):
        order = Order.objects.create(user=self.customer, total_amount=Decimal('100000.00'))
        OrderItem.objects.create(
            order=order, service_variant=self.variant, item_name=self.variant.sku,
            sku=self.variant.sku, quantity=1, price=Decimal('100000.00'),
        )
        OrderServiceDetail.objects.create(
            order=order, description='Descripcion de prueba', address='Calle 1 # 1-1',
            preferred_date=preferred_date, preferred_time=preferred_time,
        )
        operation = ServiceOperationCommands.ensure_for_order(order)
        return order, operation

    def test_try_auto_assign_assigns_when_technician_available(self):
        order, operation = self._make_order_with_operation()
        assigned = ServiceOperationCommands.try_auto_assign_via_engine(operation)
        self.assertTrue(assigned)
        operation.refresh_from_db()
        self.assertEqual(operation.technician_id, self.technician.id)
        self.assertEqual(operation.scheduled_date, MONDAY)
        self.assertEqual(operation.status, ServiceOperation.TECHNICIAN_ASSIGNED)

    def test_try_auto_assign_respects_preferred_time(self):
        order, operation = self._make_order_with_operation(preferred_time=time(10, 0))
        ServiceOperationCommands.try_auto_assign_via_engine(operation)
        operation.refresh_from_db()
        self.assertEqual(operation.scheduled_time, time(10, 0))

    def test_try_auto_assign_returns_false_when_nobody_available(self):
        WorkingSchedule.objects.filter(technician=self.technician).delete()
        order, operation = self._make_order_with_operation()
        assigned = ServiceOperationCommands.try_auto_assign_via_engine(operation)
        self.assertFalse(assigned)
        operation.refresh_from_db()
        self.assertEqual(operation.status, ServiceOperation.READY_FOR_PLANNING)
        self.assertIsNone(operation.technician_id)

    def test_try_auto_assign_noop_when_already_assigned(self):
        order, operation = self._make_order_with_operation()
        ServiceOperationCommands.try_auto_assign_via_engine(operation)
        operation.refresh_from_db()
        first_technician_id = operation.technician_id

        second_call = ServiceOperationCommands.try_auto_assign_via_engine(operation)
        self.assertFalse(second_call)
        operation.refresh_from_db()
        self.assertEqual(operation.technician_id, first_technician_id)

    def test_confirm_slot_on_payment_triggers_auto_assign(self):
        order, operation = self._make_order_with_operation()
        ServiceCommands.confirm_slot_on_payment(order)
        operation.refresh_from_db()
        self.assertEqual(operation.technician_id, self.technician.id)

    def test_confirm_slot_on_payment_does_not_raise_when_nobody_available(self):
        WorkingSchedule.objects.filter(technician=self.technician).delete()
        order, operation = self._make_order_with_operation()
        ServiceCommands.confirm_slot_on_payment(order)  # no debe lanzar excepcion
        operation.refresh_from_db()
        self.assertIsNone(operation.technician_id)

    # ── Endpoint HTTP ────────────────────────────────────────────────────────

    def test_auto_assign_endpoint_admin_only(self):
        order, operation = self._make_order_with_operation()
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/api/v1/service-operations/{operation.uuid}/auto-assign/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auto_assign_endpoint_assigns_and_reports(self):
        order, operation = self._make_order_with_operation()
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/v1/service-operations/{operation.uuid}/auto-assign/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['assigned'])
        self.assertEqual(response.data['operation']['status'], ServiceOperation.TECHNICIAN_ASSIGNED)

    def test_auto_assign_endpoint_reports_false_when_nobody_available(self):
        WorkingSchedule.objects.filter(technician=self.technician).delete()
        order, operation = self._make_order_with_operation()
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/v1/service-operations/{operation.uuid}/auto-assign/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['assigned'])
