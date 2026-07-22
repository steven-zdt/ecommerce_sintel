from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from technical_services.models import (
    ServiceCategory, ServiceLevel, ServiceConfiguration,
    TechnicalService, ServiceVariant, ServiceMaterial,
    OrderServiceDetail, OrderServiceTimeline, ServiceAttachment,
    ServicePriceHistory, ServiceImage, ServiceBooking,
    WorkingSchedule, WorkingException,
)
from orders.models import Order, OrderItem
from technical_services.services.selectors import ServiceSelector


def _check_service_availability(variant: ServiceVariant) -> bool:
    """
    Un servicio esta disponible cuando la variante, el servicio padre
    y el flag is_purchasable estan todos activos.
    Los servicios tecnicos no tienen stock fisico.
    """
    if not variant.is_active:
        return False
    if not variant.service.is_active:
        return False
    if not variant.service.is_purchasable:
        return False
    return True


def _calculate_end_time(variant: ServiceVariant, scheduled_at, duration=None):
    """Calcula end_time sumando la duracion al scheduled_at segun la estrategia de precio."""
    duration_val = float(duration) if duration is not None else float(variant.estimated_hours)
    if variant.pricing_strategy == ServiceVariant.DAILY:
        return scheduled_at + timedelta(days=duration_val)
    return scheduled_at + timedelta(hours=duration_val)


class ServiceCommands:
    @staticmethod
    @transaction.atomic
    def request_service(
        user,
        variant: ServiceVariant,
        quantity: int = 1,
        duration=None,
        discount_pct=None,
        service_detail_data=None,
        selected_technician=None,
        selected_slot_id=None,
        package=None,
        additional_cost_selections=None,
    ) -> Order:
        """
        `package`/`additional_cost_selections` son ADITIVOS (2026-07-16, dominio de
        Paquetes de Servicio): si el caller no los manda, el flujo es exactamente
        el mismo que antes -- servicios sin paquetes configurados siguen
        funcionando sin cambios. Si se manda `package`, el total de la orden pasa
        a ser el que calcula PackagePriceCalculator (paquete + costo base del
        variant + adicionales + IVA) en vez de `quotation['total_price']`, y se
        crea el snapshot ServiceRequestPackage/ServiceRequestAdditionalCost.
        LaborCostCalculator y la cotizacion del variant (`quotation`) no cambian.
        """
        if not _check_service_availability(variant):
            raise ValueError(f"El servicio '{variant.service.name}' no esta disponible en este momento.")

        if package is not None and package.service_id != variant.service_id:
            raise ValueError("El paquete seleccionado no pertenece a este servicio.")

        scheduled_at = (service_detail_data or {}).get('scheduled_at')
        end_time = None

        # ── Validar disponibilidad temporal ──────────────────────────────────────
        if scheduled_at is not None:
            end_time = _calculate_end_time(variant, scheduled_at, duration)
            if not ServiceSelector.check_time_availability(
                variant.id, scheduled_at, end_time, capacity_needed=quantity
            ):
                raise ValueError(
                    f"El horario solicitado no tiene capacidad disponible para "
                    f"'{variant.service.name}'. Por favor elige otra fecha u hora."
                )

        # ── Validar slot de profesional si se proporciono (compatibilidad) ───────
        slot_data = None
        if selected_slot_id is not None:
            from accounts.models import ProfessionalAvailability
            try:
                slot_obj = (
                    ProfessionalAvailability.objects
                    .select_for_update()
                    .get(id=selected_slot_id, is_deleted=False)
                )
            except ProfessionalAvailability.DoesNotExist:
                raise ValueError("El slot de disponibilidad seleccionado no existe.")
            if slot_obj.status != ProfessionalAvailability.PENDING_RESERVATION:
                raise ValueError(
                    "El slot ya no esta reservado temporalmente. Selecciona un nuevo horario."
                )
            slot_data = {
                'id':         slot_obj.id,
                'date':       slot_obj.date,
                'start_time': slot_obj.start_time,
            }

        quotation = ServiceSelector.get_variant_quotation(
            variant, duration=duration, discount_pct=discount_pct,
        )

        package_price_breakdown = None
        if package is not None:
            from technical_services.services.packages import PackagePriceCalculator
            package_price_breakdown = PackagePriceCalculator.calculate(
                package,
                additional_cost_selections=additional_cost_selections,
                extra_base=quotation['base_amount'],
                discount_pct=discount_pct,
            )

        order_total = package_price_breakdown['total'] if package_price_breakdown else quotation['total_price']
        order_discount = package_price_breakdown['discount_amount'] if package_price_breakdown else quotation['discount_amount']

        order = Order.objects.create(
            user=user,
            status=Order.STATUS_PENDING_PAYMENT,
            total_amount=order_total,
            discount_amount=order_discount,
        )

        OrderItem.objects.create(
            order=order,
            service_variant=variant,
            item_name=variant.service.name,
            sku=variant.sku,
            quantity=quantity,
            price=quotation['base_amount'] / quantity,
        )

        if package_price_breakdown is not None:
            from technical_services.services.packages import ServiceRequestPackageCommands
            ServiceRequestPackageCommands.create_snapshot(order, package, package_price_breakdown)

        detail = None
        if service_detail_data:
            # Capture professional type snapshot if technician is provided.
            # TechnicianProfile no tiene (ni tuvo) un campo `professional_type` -- el "tipo
            # profesional" real vive en accounts.UserProfile.user_type. El acceso anterior
            # (`technician_profile.professional_type`) lanzaba AttributeError en todo pedido de
            # servicio con tecnico pre-seleccionado.
            professional_type_snapshot = None
            if selected_technician is not None:
                from accounts.services.profile_resolver import ProfileResolver
                professional_type_snapshot = ProfileResolver.get_type(selected_technician)
            
            # Capture applied rate from quotation (audit trail)
            applied_rate_type = quotation.get('pricing_strategy')
            applied_rate_amount = quotation.get('labor_cost')
            
            detail = OrderServiceDetail.objects.create(
                order=order,
                technician=selected_technician,
                priority=service_detail_data.get('priority', 'medium'),
                description=service_detail_data.get('description', ''),
                address=service_detail_data.get('address', ''),
                scheduled_at=scheduled_at,
                preferred_date=service_detail_data.get('preferred_date'),
                preferred_time=service_detail_data.get('preferred_time'),
                location_reference=service_detail_data.get('location_reference', ''),
                neighborhood=service_detail_data.get('neighborhood', ''),
                service_notes=service_detail_data.get('service_notes', ''),
                allow_schedule_changes=service_detail_data.get('allow_schedule_changes', True),
                professional_type_snapshot=professional_type_snapshot,
                applied_rate_type=applied_rate_type,
                applied_rate_amount=applied_rate_amount,
                booked_slot_id=slot_data['id'] if slot_data else None,
                booked_date=slot_data['date'] if slot_data else None,
                booked_start_time=slot_data['start_time'] if slot_data else None,
                contact_person=service_detail_data.get('contact_person'),
            )

            # ── Crear ServiceBooking atomico ──────────────────────────────────────
            if scheduled_at is not None and end_time is not None:
                ServiceBooking.objects.create(
                    order_service_detail=detail,
                    service_variant=variant,
                    start_time=scheduled_at,
                    end_time=end_time,
                    status=ServiceBooking.STATUS_SCHEDULED,
                )

        OrderServiceTimeline.objects.create(
            order=order,
            status='pending',
            notes='Solicitud de servicio creada.',
            created_by=user,
        )

        if selected_technician is not None:
            tech_name = getattr(selected_technician, 'get_full_name',
                                lambda: selected_technician.email)()
            OrderServiceTimeline.objects.create(
                order=order,
                status='assigned',
                notes=f"Profesional pre-asignado por el cliente: {tech_name}.",
                created_by=user,
            )
            from accounts.services.profile_resolver import ProfileResolver
            tech_profile = ProfileResolver.get_technician_profile(selected_technician)
            if tech_profile is not None:
                tech_profile.is_available = False
                tech_profile.save(update_fields=['is_available', 'updated_at'])

        from notifications.services.commands import NotificationCommands
        _user      = user
        _ctx       = {
            'order_uuid':  str(order.uuid),
            'service':     variant.service.name,
            'user_email':  user.email,
            'user_name':   user.get_short_name(),
            'technician':  getattr(selected_technician, 'email', None) or '',
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='service_request_created',
                context=_ctx,
                ws_group='admin_notifications',
            )
        )

        # Centralizacion: toda solicitud de servicio entra de inmediato a
        # Operaciones de Servicios Tecnicos (READY_FOR_PLANNING), sin esperar
        # a que el pago se confirme -- el admin ve y puede empezar a planear
        # desde el momento en que el cliente solicita, no solo tras pagar.
        from technical_services.services.operations import ServiceOperationCommands
        ServiceOperationCommands.ensure_for_order(order, actor=user)

        return order

    @staticmethod
    def confirm_slot_on_payment(order) -> None:
        """Activa el ServiceBooking y confirma el slot de profesional al recibir pago exitoso."""
        try:
            detail = order.service_detail
        except Exception:
            return
        if not detail:
            return

        ServiceBooking.objects.filter(
            order_service_detail=detail,
            status=ServiceBooking.STATUS_SCHEDULED,
        ).update(status=ServiceBooking.STATUS_ACTIVE)

        if detail.booked_slot_id:
            from accounts.services.commands import AvailabilityCommands
            try:
                AvailabilityCommands.confirm_booking(detail.booked_slot_id)
            except Exception:
                pass

        item = order.items.select_related('service_variant__service').first()
        scheduled = detail.confirmed_date or detail.booked_date or detail.preferred_date
        from notifications.services.commands import NotificationCommands
        _user  = order.user
        _ctx   = {
            'order_uuid':      str(order.uuid),
            'user_name':       _user.get_short_name(),
            'service':         item.service_variant.service.name if item and item.service_variant else item.item_name if item else '',
            'technician':      detail.technician.get_full_name() if detail.technician else 'Por asignar',
            'scheduled_date':  str(scheduled) if scheduled else 'Por confirmar',
            'total':           str(order.total_amount),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='service_payment_confirmed',
                context=_ctx,
            )
        )

        from technical_services.services.operations import ServiceOperationCommands
        operation = ServiceOperationCommands.ensure_for_order(order)

        # Fase 7 (2026-07-14): 'Caso 1' -- pago aprobado intenta auto-asignar
        # tecnico via TechnicianAvailabilityEngine. Nunca puede romper la
        # confirmacion del pago: try_auto_assign_via_engine() ya no propaga
        # excepciones, pero se protege igual por si acaso.
        if operation.status == operation.READY_FOR_PLANNING and not operation.technician_id:
            try:
                ServiceOperationCommands.try_auto_assign_via_engine(operation)
            except Exception:
                pass

    @staticmethod
    def release_slot_on_failure(order) -> None:
        """Cancela el ServiceBooking y libera el slot de profesional si el pago falla."""
        try:
            detail = order.service_detail
        except Exception:
            return
        if not detail:
            return

        ServiceBooking.objects.filter(
            order_service_detail=detail,
            status=ServiceBooking.STATUS_SCHEDULED,
        ).update(status=ServiceBooking.STATUS_CANCELLED)

        if detail.booked_slot_id:
            from accounts.services.commands import AvailabilityCommands
            try:
                AvailabilityCommands.release_booking(detail.booked_slot_id)
            except Exception:
                pass


class ServiceCategoryCommands:
    @staticmethod
    @transaction.atomic
    def create_category(name: str, description: str = "", parent=None, is_active: bool = True) -> ServiceCategory:
        return ServiceCategory.objects.create(
            name=name, description=description, parent=parent, is_active=is_active
        )

    @staticmethod
    @transaction.atomic
    def update_category(category: ServiceCategory, data: dict) -> ServiceCategory:
        for field, value in data.items():
            if field in ['name', 'description', 'parent', 'is_active']:
                setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    @transaction.atomic
    def delete_category(category: ServiceCategory) -> None:
        category.is_active = False
        category.is_deleted = True
        category.save()


class ServiceLevelCommands:
    @staticmethod
    @transaction.atomic
    def create_level(name: str) -> ServiceLevel:
        return ServiceLevel.objects.create(name=name)

    @staticmethod
    @transaction.atomic
    def update_level(level: ServiceLevel, data: dict) -> ServiceLevel:
        for field, value in data.items():
            if field in ['name']:
                setattr(level, field, value)
        level.save()
        return level

    @staticmethod
    @transaction.atomic
    def delete_level(level: ServiceLevel) -> None:
        level.is_deleted = True
        level.save(update_fields=['is_deleted', 'updated_at'])


class ServiceImageCommands:
    @staticmethod
    @transaction.atomic
    def add_image(service: TechnicalService, image_file, alt_text: str = '', is_primary: bool = False) -> ServiceImage:
        if is_primary:
            ServiceImage.objects.filter(service=service, is_primary=True).update(is_primary=False)
        img = ServiceImage.objects.create(
            service=service,
            image=image_file,
            alt_text=alt_text or '',
            is_primary=is_primary,
        )
        if not ServiceImage.objects.filter(service=service, is_primary=True).exclude(pk=img.pk).exists():
            img.is_primary = True
            img.save(update_fields=['is_primary'])
        return img

    @staticmethod
    @transaction.atomic
    def delete_image(image: ServiceImage) -> None:
        was_primary = image.is_primary
        service = image.service
        image.delete()
        if was_primary:
            first = ServiceImage.objects.filter(service=service).first()
            if first:
                first.is_primary = True
                first.save(update_fields=['is_primary'])

    @staticmethod
    @transaction.atomic
    def set_primary(image: ServiceImage) -> ServiceImage:
        ServiceImage.objects.filter(service=image.service, is_primary=True).update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=['is_primary'])
        return image


class TechnicalServiceCommands:
    @staticmethod
    @transaction.atomic
    def create_service(
        name: str,
        description: str,
        category=None,
        level=None,
        vendor=None,
        is_active: bool = True,
        is_featured: bool = False,
        is_purchasable: bool = True,
        meta_title: str = '',
        meta_description: str = '',
        meta_keywords: str = '',
    ) -> TechnicalService:
        return TechnicalService.objects.create(
            name=name, description=description,
            category=category, level=level, vendor=vendor,
            is_active=is_active, is_featured=is_featured, is_purchasable=is_purchasable,
            meta_title=meta_title, meta_description=meta_description, meta_keywords=meta_keywords,
        )

    @staticmethod
    @transaction.atomic
    def create_service_with_default_variant(
        service_data: dict,
        variant_data: dict | None,
        vendor=None,
    ) -> TechnicalService:
        service = TechnicalServiceCommands.create_service(
            vendor=vendor,
            **service_data,
        )
        if variant_data is not None:
            ServiceVariantCommands.create_variant(
                service=service,
                sku='',
                is_default=True,
                **variant_data,
            )
        return service

    @staticmethod
    @transaction.atomic
    def update_service(service: TechnicalService, data: dict) -> TechnicalService:
        for field, value in data.items():
            setattr(service, field, value)
        service.save()
        return service

    @staticmethod
    @transaction.atomic
    def delete_service(service: TechnicalService) -> None:
        service.is_active = False
        service.is_deleted = True
        service.save()


def _generate_variant_sku(service: TechnicalService, pricing_strategy: str, complexity_factor: float) -> str:
    """
    Auto-generate SKU from service slug + pricing strategy + complexity level.
    Format: {service_slug}-{strategy}-{complexity_code}-{variant_count}
    Example: inst-cam-ip-hourly-std-01, inst-cam-ip-daily-adv-02
    """
    complexity_map = {
        1.0: 'STD',    # Standard
        1.25: 'INT',   # Intermediate
        1.5: 'ADV',    # Advanced
        2.0: 'EXP',    # Expert
    }
    complexity_code = complexity_map.get(float(complexity_factor), f'C{complexity_factor:.0f}')
    strategy_code = pricing_strategy.lower()[:3]  # HOU, DAI, FIX
    
    # Count existing variants for this service
    variant_count = service.variants.filter(is_deleted=False).count() + 1
    
    # Generate candidate SKU
    base_sku = f"{service.slug}-{strategy_code}-{complexity_code}".upper()
    candidate = f"{base_sku}-{variant_count:02d}"
    
    # Ensure uniqueness (in rare case of collision)
    counter = variant_count
    while ServiceVariant.objects.filter(sku=candidate, is_deleted=False).exists():
        counter += 1
        candidate = f"{base_sku}-{counter:02d}"
    
    return candidate


class ServiceVariantCommands:
    @staticmethod
    @transaction.atomic
    def create_variant(
        service: TechnicalService,
        sku: str = None,
        pricing_strategy: str = ServiceVariant.HOURLY,
        estimated_hours=1,
        complexity_factor=1,
        fixed_price=None,
        min_duration=None,
        max_duration=None,
        simultaneous_capacity: int = 1,
        is_default: bool = False,
        is_active: bool = True,
    ) -> ServiceVariant:
        """
        Create a new service variant. If sku is not provided, it will be auto-generated.
        """
        # Auto-generate SKU if not provided
        if not sku or not sku.strip():
            sku = _generate_variant_sku(service, pricing_strategy, complexity_factor)
        
        if is_default:
            service.variants.filter(is_deleted=False, is_default=True).update(is_default=False)
        
        return ServiceVariant.objects.create(
            service=service,
            sku=sku,
            pricing_strategy=pricing_strategy,
            estimated_hours=estimated_hours,
            complexity_factor=complexity_factor,
            fixed_price=fixed_price,
            min_duration=min_duration,
            max_duration=max_duration,
            simultaneous_capacity=max(1, int(simultaneous_capacity)),
            is_default=is_default,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_variant(variant: ServiceVariant, data: dict, updated_by=None) -> ServiceVariant:
        old_price = variant.fixed_price
        if data.get('is_default') and not variant.is_default:
            variant.service.variants.filter(is_deleted=False, is_default=True).update(is_default=False)
        for field, value in data.items():
            setattr(variant, field, value)
        new_price = variant.fixed_price
        if old_price != new_price:
            ServicePriceHistory.objects.create(
                variant=variant,
                old_price=old_price,
                new_price=new_price,
                changed_by=updated_by
            )
        variant.save()
        return variant

    @staticmethod
    @transaction.atomic
    def delete_variant(variant: ServiceVariant) -> None:
        variant.is_deleted = True
        variant.save()


class ServiceMaterialCommands:
    @staticmethod
    @transaction.atomic
    def add_material(variant: ServiceVariant, product_variant, quantity) -> ServiceMaterial:
        material, _ = ServiceMaterial.objects.get_or_create(
            variant=variant,
            product_variant=product_variant,
            defaults={'quantity': quantity},
        )
        if not _:
            material.quantity = quantity
            material.save()
        return material

    @staticmethod
    @transaction.atomic
    def remove_material(material: ServiceMaterial) -> None:
        material.is_deleted = True
        material.save(update_fields=['is_deleted', 'updated_at'])


class ServiceConfigurationCommands:
    @staticmethod
    @transaction.atomic
    def create_configuration(
        name: str,
        smlv,
        transport_subsidy,
        benefit_rate,
        indirect_costs_rate,
        is_active: bool = True,
    ) -> ServiceConfiguration:
        if is_active:
            ServiceConfiguration.objects.filter(is_active=True).update(is_active=False)
        return ServiceConfiguration.objects.create(
            name=name, smlv=smlv,
            transport_subsidy=transport_subsidy,
            benefit_rate=benefit_rate,
            indirect_costs_rate=indirect_costs_rate,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_configuration(config: ServiceConfiguration, data: dict) -> ServiceConfiguration:
        if data.get('is_active') and not config.is_active:
            ServiceConfiguration.objects.filter(is_active=True).update(is_active=False)
        for field, value in data.items():
            setattr(config, field, value)
        config.save()
        return config


class ServiceTimelineCommands:
    @staticmethod
    @transaction.atomic
    def add_timeline_event(order: Order, status: str, notes: str = "", created_by=None) -> OrderServiceTimeline:
        valid_statuses = [choice[0] for choice in OrderServiceTimeline.STATUS_CHOICES]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
            
        event = OrderServiceTimeline.objects.create(
            order=order,
            status=status,
            notes=notes,
            created_by=created_by
        )
        
        if status == 'cancelled':
            order.status = 'cancelled'
            order.save()
            detail = OrderServiceDetail.objects.filter(order=order).first()
            if detail:
                ServiceBooking.objects.filter(
                    order_service_detail=detail,
                    status__in=[ServiceBooking.STATUS_SCHEDULED, ServiceBooking.STATUS_ACTIVE],
                ).update(status=ServiceBooking.STATUS_CANCELLED)
                if detail.technician:
                    from accounts.services.profile_resolver import ProfileResolver
                    tech_profile = ProfileResolver.get_technician_profile(detail.technician)
                    if tech_profile:
                        tech_profile.is_available = True
                        tech_profile.save(update_fields=['is_available', 'updated_at'])
        elif status == 'completed':
            order.status = 'delivered'
            order.save()
            detail = OrderServiceDetail.objects.filter(order=order).first()
            if detail:
                ServiceBooking.objects.filter(
                    order_service_detail=detail,
                    status=ServiceBooking.STATUS_ACTIVE,
                ).update(status=ServiceBooking.STATUS_COMPLETED)
                if detail.technician:
                    from accounts.services.profile_resolver import ProfileResolver
                    tech_profile = ProfileResolver.get_technician_profile(detail.technician)
                    if tech_profile:
                        tech_profile.is_available = True
                        tech_profile.save(update_fields=['is_available', 'updated_at'])
            
        from notifications.services.commands import NotificationCommands
        _user  = order.user
        _ctx   = {'order_uuid': str(order.uuid), 'status': status, 'notes': notes}
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='service_status_updated',
                context=_ctx,
                ws_group='admin_notifications',
            )
        )
        
        return event


class ServiceAttachmentCommands:
    ALLOWED_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'video/mp4',
        'video/quicktime',
        'video/x-msvideo',
    ]
    ALLOWED_EXTENSIONS = [
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.mov', '.avi',
    ]
    MAX_SIZE = 100 * 1024 * 1024

    @staticmethod
    @transaction.atomic
    def add_attachment(order: Order, file, uploaded_by=None, doc_type: str = '') -> ServiceAttachment:
        # Centraliza tamano/extension/magic-bytes en accounts.services.commands.validate_file
        # (mismo validador que usan KYC/avatares) en vez de un chequeo ad-hoc de solo
        # content-type declarado por el cliente -- ese content-type se puede falsificar.
        from accounts.services.commands import validate_file
        from rest_framework.exceptions import ValidationError as DRFValidationError
        try:
            validate_file(
                file, max_size_mb=ServiceAttachmentCommands.MAX_SIZE // (1024 * 1024),
                allowed_extensions=ServiceAttachmentCommands.ALLOWED_EXTENSIONS,
                magic_bytes_check=True,
            )
        except DRFValidationError as e:
            raise ValueError(str(e.detail[0]) if isinstance(e.detail, list) else str(e.detail))

        content_type = getattr(file, 'content_type', None)
        return ServiceAttachment.objects.create(
            order=order,
            file=file,
            file_name=file.name,
            file_size=file.size,
            mime_type=content_type,
            doc_type=doc_type or '',
            uploaded_by=uploaded_by,
        )

class ServiceAssignmentCommands:
    @staticmethod
    def _release_technician(technician) -> None:
        """Libera (is_available=True) a un tecnico previamente asignado, si tiene perfil."""
        if technician is None:
            return
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_technician_profile(technician)
        if profile:
            profile.is_available = True
            profile.save(update_fields=['is_available', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def assign_technician(order: Order, technician, notes: str = "", assigned_by=None) -> OrderServiceDetail:
        """
        Assigns a technician to the service order, toggles their availability,
        and adds an 'assigned' timeline event.
        """
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_technician_profile(technician)
        if profile is None:
            raise ValueError("El técnico no tiene un perfil de técnico configurado.")

        if not profile.is_available:
            raise ValueError("El técnico seleccionado no está disponible.")

        # Get or create detail
        detail, created = OrderServiceDetail.objects.get_or_create(
            order=order,
            defaults={'address': '', 'description': ''}
        )

        # If there was a previous technician, make them available again
        if detail.technician and detail.technician != technician:
            ServiceAssignmentCommands._release_technician(detail.technician)

        detail.technician = technician
        detail.save()

        # Mark technician as unavailable
        profile.is_available = False
        profile.save(update_fields=['is_available', 'updated_at'])

        # Add timeline event
        ServiceTimelineCommands.add_timeline_event(
            order=order,
            status='assigned',
            notes=notes or f"Técnico {technician.get_full_name()} asignado.",
            created_by=assigned_by
        )

        return detail

    @staticmethod
    @transaction.atomic
    def unassign_technician(order: Order, unassigned_by=None, notes: str = "") -> OrderServiceDetail:
        """
        Cancela la asignacion de tecnico de una orden de servicio: libera al tecnico
        (is_available=True) y vuelve el detalle de la orden a estado 'pending'.
        """
        detail = OrderServiceDetail.objects.filter(order=order).first()
        if detail is None or detail.technician is None:
            raise ValueError("Esta orden no tiene un técnico asignado.")

        previous = detail.technician
        ServiceAssignmentCommands._release_technician(previous)
        detail.technician = None
        detail.save()

        ServiceTimelineCommands.add_timeline_event(
            order=order,
            status='pending',
            notes=notes or f"Asignación de {previous.get_full_name()} cancelada.",
            created_by=unassigned_by,
        )
        return detail

    @staticmethod
    @transaction.atomic
    def change_priority(order: Order, priority: str, changed_by=None) -> OrderServiceDetail:
        """Cambia la prioridad de una orden de servicio ya solicitada."""
        valid_priorities = [choice[0] for choice in OrderServiceDetail.PRIORITY_CHOICES]
        if priority not in valid_priorities:
            raise ValueError(f"Prioridad inválida: {priority}. Debe ser una de {valid_priorities}")

        detail = OrderServiceDetail.objects.filter(order=order).first()
        if detail is None:
            raise ValueError("Esta orden no tiene detalle de servicio.")

        detail.priority = priority
        detail.save(update_fields=['priority', 'updated_at'])
        return detail

    @staticmethod
    @transaction.atomic
    def auto_assign_technician(order: Order, assigned_by=None) -> OrderServiceDetail:
        """
        Automatically selects and assigns a technician based on service category and availability.
        """
        from technical_services.services.selectors import TechnicianSelector
        best_tech = TechnicianSelector.find_best_technician(order)
        if not best_tech:
            raise ValueError("No hay técnicos disponibles calificados para este servicio.")

        return ServiceAssignmentCommands.assign_technician(
            order=order,
            technician=best_tech,
            notes="Asignación automática de técnico.",
            assigned_by=assigned_by
        )


class WorkingScheduleCommands:
    """CRUD de horario laboral recurrente (TechnicianAvailabilityEngine, 2026-07-14)."""

    @staticmethod
    @transaction.atomic
    def upsert_schedule(technician, weekday: int, start_time, end_time, is_active: bool = True) -> WorkingSchedule:
        if end_time <= start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio.")

        schedule, _ = WorkingSchedule.objects.update_or_create(
            technician=technician, weekday=weekday,
            defaults={
                'start_time': start_time, 'end_time': end_time,
                'is_active': is_active, 'is_deleted': False,
            },
        )
        return schedule

    @staticmethod
    @transaction.atomic
    def delete_schedule(schedule: WorkingSchedule) -> None:
        schedule.is_deleted = True
        schedule.save(update_fields=['is_deleted', 'updated_at'])


class WorkingExceptionCommands:
    """CRUD de ausencias/bloqueos de tecnico (TechnicianAvailabilityEngine, 2026-07-14)."""

    @staticmethod
    @transaction.atomic
    def create_exception(technician, exception_type: str, start_date, end_date,
                          start_time=None, end_time=None, reason: str = '', created_by=None) -> WorkingException:
        if end_date < start_date:
            raise ValueError("La fecha de fin debe ser igual o posterior a la fecha de inicio.")
        if (start_time is None) != (end_time is None):
            raise ValueError("start_time y end_time deben venir juntos o ambos vacios (dia completo).")
        if start_time is not None and end_time <= start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio.")
        if exception_type == WorkingException.TYPE_EXTRA_HOURS and start_time is None:
            raise ValueError("Horas extra requiere hora de inicio y fin -- no puede ser de dia completo.")

        return WorkingException.objects.create(
            technician=technician, exception_type=exception_type,
            start_date=start_date, end_date=end_date,
            start_time=start_time, end_time=end_time,
            reason=reason, created_by=created_by,
        )

    @staticmethod
    @transaction.atomic
    def delete_exception(exception) -> None:
        exception.is_deleted = True
        exception.save(update_fields=['is_deleted', 'updated_at'])
