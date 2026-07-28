from decimal import Decimal
from django.db import transaction
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from technical_services.services.selectors import ServiceSelector
from ..models import (
    Quotation, QuotationItem, QuotationService, QuotationMaterial,
    QuotationRentalItem, QuotationAttachment, QuotationItemCostSnapshot,
    QuotationTimeline, QuoteTemplateCategory, QuoteTemplateSubcategory,
    QuoteTemplate, QuoteTemplateAttribute, QuoteEquipmentType, QuoteTemplateModule,
    QuoteQuestion, QuoteQuestionOption,
)


def _json_safe(value):
    """Convierte recursivamente Decimal -> str para poder persistir en un JSONField."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


class QuotationBuilder:
    @staticmethod
    def _create_product_item(quotation, item_data):
        """Crea un QuotationItem con snapshot de precio. Retorna (item, monto)."""
        from shop.services.pricing import ShopPricingCalculator
        variant = ProductVariant.objects.select_related('product').get(pk=item_data['variant_id'])
        qty = item_data['quantity']
        breakdown = ShopPricingCalculator.calculate_breakdown(variant, qty)
        base_price = breakdown['base_price']
        final_unit = (breakdown['final_price'] / qty).quantize(Decimal('0.01')) if qty else base_price

        q_item = QuotationItem.objects.create(
            quotation=quotation,
            variant=variant,
            product_name=f"{variant.product.name} ({variant.sku})",
            sku=variant.sku,
            quantity=qty,
            unit_price=base_price,
            unit_price_final=final_unit,
        )
        for cost_line in breakdown['costs']:
            QuotationItemCostSnapshot.objects.create(
                quotation_item=q_item,
                cost_name=cost_line['name'],
                context=cost_line['context'],
                cost_type=cost_line['cost_type'],
                value=cost_line['value'],
                computed_amount=cost_line['amount'],
                is_discount=cost_line['is_discount'],
            )
        return q_item, breakdown['final_price']

    @staticmethod
    def _create_catalog_service(quotation, variant_id):
        """Crea un QuotationService desde el catalogo de servicios. Retorna (service, monto)."""
        variant = ServiceVariant.objects.select_related('service').get(pk=variant_id)
        quote_data = ServiceSelector.get_variant_quotation(variant)

        q_service = QuotationService.objects.create(
            quotation=quotation,
            service=variant.service,
            service_name=f"{variant.service.name} ({variant.sku})",
            hours=variant.estimated_hours,
            labor_cost=quote_data['labor_cost'],
        )
        for m_data in quote_data['breakdown']['materials']:
            QuotationMaterial.objects.create(
                quotation_service=q_service,
                material_name=m_data['name'],
                unit_price=m_data['price'],
                quantity=m_data['qty'],
            )
        return q_service, q_service.subtotal

    @staticmethod
    def _create_custom_service(quotation, svc):
        """Crea un QuotationService personalizado (sin catalogo). Retorna (service, monto)."""
        materials = svc.pop('materials', [])
        q_service = QuotationService.objects.create(
            quotation=quotation,
            service=None,
            service_name=svc.get('service_name', svc.get('custom_service_type', 'Servicio personalizado')),
            hours=Decimal(str(svc.get('hours', '0.00'))),
            labor_cost=Decimal(str(svc.get('labor_cost', '0.00'))),
            custom_service_type=svc.get('custom_service_type', ''),
            labor_description=svc.get('labor_description', ''),
            estimated_time_hours=Decimal(str(svc['estimated_time_hours'])) if svc.get('estimated_time_hours') is not None else None,
            requires_full_cost_installation=svc.get('requires_full_cost_installation', False),
        )
        for m_data in materials:
            QuotationMaterial.objects.create(
                quotation_service=q_service,
                material_name=m_data['material_name'],
                unit_price=Decimal(str(m_data['unit_price'])),
                quantity=Decimal(str(m_data['quantity'])),
            )
        return q_service, q_service.subtotal

    @staticmethod
    @transaction.atomic
    def create_quotation(
        client_data,
        product_items=None,
        service_items=None,
        rental_items=None,
        is_custom=False,
        custom_service_data=None,
        attachments=None,
    ) -> Quotation:
        """
        Creates a hybrid quotation with snapshot pricing.

        product_items   : list of {'variant_id': int, 'quantity': int}
        service_items   : list of ServiceVariant PKs (catalog services)
        rental_items    : list of {
                            'variant_id': int,
                            'rent_start_date': date,
                            'rent_end_date': date,
                          }
        is_custom       : True to flag this as a custom/non-catalog quotation
        custom_service_data : list of {..., 'materials': [{'material_name', 'unit_price', 'quantity'}]}
        attachments     : list of InMemoryUploadedFile objects (images)
        """
        client_data['is_custom'] = is_custom
        quotation = Quotation.objects.create(**client_data)

        subtotal_products = Decimal('0.00')
        subtotal_services = Decimal('0.00')
        subtotal_rentals = Decimal('0.00')

        if product_items:
            for item in product_items:
                _q_item, amount = QuotationBuilder._create_product_item(quotation, item)
                subtotal_products += amount

        if service_items:
            for v_id in service_items:
                _q_service, amount = QuotationBuilder._create_catalog_service(quotation, v_id)
                subtotal_services += amount

        if custom_service_data:
            for svc in custom_service_data:
                _q_service, amount = QuotationBuilder._create_custom_service(quotation, svc)
                subtotal_services += amount

        if rental_items:
            from renting.models import EquipmentVariant
            for r_item in rental_items:
                variant = EquipmentVariant.objects.select_related('equipment').get(pk=r_item['variant_id'])
                start = r_item['rent_start_date']
                end = r_item['rent_end_date']

                delta = (end - start).days
                computed_days = Decimal(str(max(delta, 1)))
                price_per_day = variant.rental_price_per_day or Decimal('0.00')
                subtotal = (price_per_day * computed_days).quantize(Decimal('0.01'))

                QuotationRentalItem.objects.create(
                    quotation=quotation,
                    variant=variant,
                    equipment_name=f"{variant.equipment.name} ({variant.sku})",
                    sku=variant.sku,
                    rental_price_per_day=price_per_day,
                    rental_price_per_hour=variant.rental_price_per_hour or Decimal('0.00'),
                    rent_start_date=start,
                    rent_end_date=end,
                    computed_days=computed_days,
                    subtotal=subtotal,
                )
                subtotal_rentals += subtotal

        if attachments:
            from accounts.services.commands import validate_file
            for f in attachments:
                validate_file(
                    f, max_size_mb=10,
                    allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'],
                    magic_bytes_check=True,
                )
                QuotationAttachment.objects.create(quotation=quotation, file=f)

        quotation.subtotal_products = subtotal_products
        quotation.subtotal_services = subtotal_services
        quotation.subtotal_rentals = subtotal_rentals
        quotation.total_amount = subtotal_products + subtotal_services + subtotal_rentals
        quotation.save()

        return quotation

    @staticmethod
    @transaction.atomic
    def partial_update(quotation: Quotation, data: dict) -> Quotation:
        """Update allowed contact/metadata fields on an existing quotation."""
        ALLOWED = ('notes', 'company', 'phone', 'city', 'department', 'address', 'project_name')
        changed = []
        for field in ALLOWED:
            if field in data:
                setattr(quotation, field, data[field])
                changed.append(field)
        if changed:
            quotation.save(update_fields=[*changed, 'updated_at'])
        return quotation

    @staticmethod
    @transaction.atomic
    def mark_as_sent(quotation: Quotation, changed_by=None) -> Quotation:
        quotation.status = Quotation.STATUS_SENT
        quotation.save(update_fields=['status', 'updated_at'])
        QuotationTimeline.objects.create(
            quotation=quotation, status=Quotation.STATUS_SENT,
            notes='Cotizacion enviada al cliente.', changed_by=changed_by,
        )
        return quotation

    @staticmethod
    @transaction.atomic
    def create_from_template(applicant_data: dict, template: QuoteTemplate, answers: dict, files: dict = None) -> Quotation:
        """
        Crea una Quotation-solicitud a partir de un cuestionario tecnico
        respondido por el cliente. NO calcula ningun precio — solo captura
        el requerimiento (respuestas organizadas por modulo) para que un
        asesor comercial lo revise y cotice manualmente despues.

        answers : {"<module_uuid>": {"<question_key>": valor, ...}, ...}
        files   : {"<module_uuid>__<question_key>": [UploadedFile, ...], ...} para
                  preguntas de tipo archivo (IMAGE/FILE/SIGNATURE) -- cada
                  clave admite una o varias subidas (ver requirement_documents,
                  Fase 5 de la simplificacion del wizard, 2026-07-23).
        """
        quotation = Quotation.objects.create(
            **applicant_data,
            template=template,
            answers=_json_safe(answers),
            status=Quotation.STATUS_RECEIVED,
        )
        if files:
            from accounts.services.commands import validate_file
            for field_key, file_list in files.items():
                for f in file_list if isinstance(file_list, (list, tuple)) else [file_list]:
                    validate_file(
                        f, max_size_mb=20,
                        allowed_extensions=[
                            '.pdf', '.jpg', '.jpeg', '.png',
                            '.doc', '.docx', '.xls', '.xlsx', '.txt',
                        ],
                        magic_bytes_check=True,
                    )
                    QuotationAttachment.objects.create(quotation=quotation, file=f, note=field_key)

        QuotationTimeline.objects.create(
            quotation=quotation, status=Quotation.STATUS_RECEIVED,
            notes='Solicitud recibida del cliente.',
        )
        return quotation


class QuotationReviewCommands:
    """Acciones del asesor comercial sobre una Quotation ya recibida."""

    @staticmethod
    @transaction.atomic
    def change_status(quotation: Quotation, new_status: str, notes: str = '', changed_by=None) -> Quotation:
        quotation.status = new_status
        quotation.save(update_fields=['status', 'updated_at'])
        QuotationTimeline.objects.create(
            quotation=quotation, status=new_status, notes=notes, changed_by=changed_by,
        )
        return quotation

    @staticmethod
    @transaction.atomic
    def add_product_item(quotation: Quotation, item_data: dict) -> QuotationItem:
        # select_for_update: sin esto, dos requests concurrentes agregando items a la
        # misma Quotation leen el mismo subtotal_products/total_amount "viejo" y la
        # segunda escritura pisa la primera (lost update), igual que el patron ya
        # corregido en payment/renting para stock/disponibilidad.
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        q_item, amount = QuotationBuilder._create_product_item(quotation, item_data)
        quotation.subtotal_products += amount
        quotation.total_amount += amount
        quotation.save(update_fields=['subtotal_products', 'total_amount', 'updated_at'])
        return q_item

    @staticmethod
    @transaction.atomic
    def add_service_item(quotation: Quotation, service_data: dict) -> QuotationService:
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        if service_data.get('variant_id'):
            q_service, amount = QuotationBuilder._create_catalog_service(quotation, service_data['variant_id'])
        else:
            quotation.is_custom = True
            q_service, amount = QuotationBuilder._create_custom_service(quotation, dict(service_data))
        quotation.subtotal_services += amount
        quotation.total_amount += amount
        quotation.save(update_fields=['subtotal_services', 'total_amount', 'is_custom', 'updated_at'])
        return q_service


# ─── Constructor de Cuestionarios: Commands de definicion de plantillas ──────

class QuoteTemplateCategoryCommands:
    @staticmethod
    @transaction.atomic
    def create_category(**data) -> QuoteTemplateCategory:
        return QuoteTemplateCategory.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_category(category: QuoteTemplateCategory, data: dict) -> QuoteTemplateCategory:
        for field, value in data.items():
            setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    @transaction.atomic
    def delete_category(category: QuoteTemplateCategory) -> None:
        category.is_deleted = True
        category.save(update_fields=['is_deleted', 'updated_at'])


class QuoteTemplateSubcategoryCommands:
    @staticmethod
    @transaction.atomic
    def create_subcategory(**data) -> QuoteTemplateSubcategory:
        return QuoteTemplateSubcategory.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_subcategory(subcategory: QuoteTemplateSubcategory, data: dict) -> QuoteTemplateSubcategory:
        for field, value in data.items():
            setattr(subcategory, field, value)
        subcategory.save()
        return subcategory

    @staticmethod
    @transaction.atomic
    def delete_subcategory(subcategory: QuoteTemplateSubcategory) -> None:
        subcategory.is_deleted = True
        subcategory.save(update_fields=['is_deleted', 'updated_at'])


def _generate_template_code(prefix_source) -> str:
    """Genera un codigo unico tipo 'CCTV-001' a partir del tipo de sistema/servicio de la plantilla."""
    from django.utils.text import slugify
    if hasattr(prefix_source, 'name'):
        prefix_source = prefix_source.name
    prefix = slugify(prefix_source or 'PLANTILLA').upper().replace('-', '')[:8] or 'PLANTILLA'
    n = QuoteTemplate.objects.filter(code__startswith=f'{prefix}-').count() + 1
    code = f'{prefix}-{str(n).zfill(3)}'
    while QuoteTemplate.objects.filter(code=code).exists():
        n += 1
        code = f'{prefix}-{str(n).zfill(3)}'
    return code


class QuoteTemplateCommands:
    @staticmethod
    @transaction.atomic
    def create_template(**data) -> QuoteTemplate:
        if not data.get('code'):
            category = data.get('category')
            inherited_service_type = category.service_type if category else None
            data['code'] = _generate_template_code(
                data.get('system_type') or inherited_service_type or data.get('name')
            )
        return QuoteTemplate.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_template(template: QuoteTemplate, data: dict) -> QuoteTemplate:
        for field, value in data.items():
            setattr(template, field, value)
        template.save()
        return template

    @staticmethod
    @transaction.atomic
    def delete_template(template: QuoteTemplate) -> None:
        template.is_deleted = True
        template.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def clone_template(template: QuoteTemplate) -> QuoteTemplate:
        """
        Duplica una plantilla completa: la plantilla + sus modulos + las
        preguntas y opciones de cada modulo. Reutiliza exactamente la misma
        estrategia que QuoteTemplateModuleCommands.duplicate_module para
        copiar preguntas/opciones -- el unique_together (module, key) de
        QuoteQuestion se respeta "por construccion" porque cada modulo
        clonado es una fila nueva (ver docstring de duplicate_module).
        Nombre/slug se desambiguan con un sufijo incremental porque
        QuoteTemplate.save() no lo hace solo (slug unico, se asigna una sola
        vez si esta vacio). code se regenera via _generate_template_code
        (mismo prefijo, siguiente numero disponible). is_published siempre
        arranca en False -- una plantilla clonada nunca debe quedar visible
        en /cotizar sin que el admin la revise primero.
        """
        base_name = f"{template.name} (copia)"
        name = base_name
        suffix = 2
        while QuoteTemplate.objects.filter(name=name).exists():
            name = f"{base_name} {suffix}"
            suffix += 1

        clone = QuoteTemplate.objects.create(
            category=template.category,
            subcategory=template.subcategory,
            name=name,
            code=_generate_template_code(template.system_type or (template.category.service_type if template.category else None) or name),
            description=template.description,
            installation_type=template.installation_type,
            system_type=template.system_type,
            version=1,
            is_published=False,
            display_order=template.display_order,
            is_active=template.is_active,
            complexity_hint=template.complexity_hint,
        )

        for module in template.modules.filter(is_deleted=False):
            new_module = QuoteTemplateModule.objects.create(
                template=clone,
                module_type=module.module_type,
                equipment_type=module.equipment_type,
                name=module.name,
                description=module.description,
                unit=module.unit,
                min_quantity=module.min_quantity,
                max_quantity=module.max_quantity,
                is_required=module.is_required,
                display_order=module.display_order,
                is_active=module.is_active,
            )
            # Mapa uuid-pregunta-original -> pregunta-nueva, para poder
            # reescribir depends_on_question en la copia (si apuntaba a otra
            # pregunta del mismo modulo, tambien clonada aqui).
            question_map = {}
            for question in module.questions.filter(is_deleted=False):
                new_question = QuoteQuestion.objects.create(
                    module=new_module,
                    key=question.key,
                    question_type=question.question_type,
                    label=question.label,
                    description=question.description,
                    help_text=question.help_text,
                    placeholder=question.placeholder,
                    is_required=question.is_required,
                    is_visible=question.is_visible,
                    default_value=question.default_value,
                    unit=question.unit,
                    group=question.group,
                    min_value=question.min_value,
                    max_value=question.max_value,
                    validation_regex=question.validation_regex,
                    table_columns=question.table_columns,
                    display_order=question.display_order,
                    is_active=question.is_active,
                    allow_other=question.allow_other,
                    depends_on_values=question.depends_on_values,
                )
                question_map[question.pk] = new_question
                for option in question.options.filter(is_deleted=False):
                    QuoteQuestionOption.objects.create(
                        question=new_question, label=option.label, value=option.value,
                        display_order=option.display_order, is_active=option.is_active,
                    )
            # Segunda pasada: reescribir depends_on_question una vez que
            # todas las preguntas del modulo ya tienen su copia creada.
            for question in module.questions.filter(is_deleted=False):
                if question.depends_on_question_id and question.depends_on_question_id in question_map:
                    cloned = question_map[question.pk]
                    cloned.depends_on_question = question_map[question.depends_on_question_id]
                    cloned.save(update_fields=['depends_on_question'])

        return clone


class QuoteTemplateAttributeCommands:
    @staticmethod
    @transaction.atomic
    def create_attribute(**data) -> QuoteTemplateAttribute:
        return QuoteTemplateAttribute.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_attribute(attribute: QuoteTemplateAttribute, data: dict) -> QuoteTemplateAttribute:
        for field, value in data.items():
            setattr(attribute, field, value)
        attribute.save()
        return attribute

    @staticmethod
    @transaction.atomic
    def delete_attribute(attribute: QuoteTemplateAttribute) -> None:
        attribute.is_deleted = True
        attribute.save(update_fields=['is_deleted', 'updated_at'])


class QuoteEquipmentTypeCommands:
    @staticmethod
    @transaction.atomic
    def create_equipment_type(**data) -> QuoteEquipmentType:
        return QuoteEquipmentType.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_equipment_type(equipment_type: QuoteEquipmentType, data: dict) -> QuoteEquipmentType:
        for field, value in data.items():
            setattr(equipment_type, field, value)
        equipment_type.save()
        return equipment_type

    @staticmethod
    @transaction.atomic
    def delete_equipment_type(equipment_type: QuoteEquipmentType) -> None:
        equipment_type.is_deleted = True
        equipment_type.save(update_fields=['is_deleted', 'updated_at'])


class QuoteTemplateModuleCommands:
    @staticmethod
    @transaction.atomic
    def create_module(**data) -> QuoteTemplateModule:
        return QuoteTemplateModule.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_module(module: QuoteTemplateModule, data: dict) -> QuoteTemplateModule:
        for field, value in data.items():
            setattr(module, field, value)
        module.save()
        return module

    @staticmethod
    @transaction.atomic
    def delete_module(module: QuoteTemplateModule) -> None:
        module.is_deleted = True
        module.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def duplicate_module(module: QuoteTemplateModule) -> QuoteTemplateModule:
        clone = QuoteTemplateModule.objects.create(
            template=module.template,
            module_type=module.module_type,
            equipment_type=module.equipment_type,
            name=f"{module.name} (copia)",
            description=module.description,
            unit=module.unit,
            min_quantity=module.min_quantity,
            max_quantity=module.max_quantity,
            is_required=module.is_required,
            display_order=module.display_order,
            is_active=module.is_active,
        )
        for question in module.questions.filter(is_deleted=False):
            new_question = QuoteQuestion.objects.create(
                module=clone,
                key=question.key,
                question_type=question.question_type,
                label=question.label,
                description=question.description,
                help_text=question.help_text,
                placeholder=question.placeholder,
                is_required=question.is_required,
                is_visible=question.is_visible,
                default_value=question.default_value,
                unit=question.unit,
                group=question.group,
                min_value=question.min_value,
                max_value=question.max_value,
                validation_regex=question.validation_regex,
                table_columns=question.table_columns,
                display_order=question.display_order,
                is_active=question.is_active,
                allow_other=question.allow_other,
            )
            for option in question.options.filter(is_deleted=False):
                QuoteQuestionOption.objects.create(
                    question=new_question, label=option.label, value=option.value,
                    display_order=option.display_order, is_active=option.is_active,
                )
        return clone

    @staticmethod
    @transaction.atomic
    def reorder_module(module: QuoteTemplateModule, direction: str) -> None:
        """direction: 'up' o 'down' — intercambia display_order con el vecino del mismo module_type."""
        siblings = list(
            QuoteTemplateModule.objects
            .filter(template=module.template, module_type=module.module_type, is_deleted=False)
            .order_by('display_order', 'id')
        )
        idx = next((i for i, m in enumerate(siblings) if m.pk == module.pk), None)
        if idx is None:
            return
        target_idx = idx - 1 if direction == 'up' else idx + 1
        if target_idx < 0 or target_idx >= len(siblings):
            return
        neighbor = siblings[target_idx]
        module.display_order, neighbor.display_order = neighbor.display_order, module.display_order
        module.save(update_fields=['display_order', 'updated_at'])
        neighbor.save(update_fields=['display_order', 'updated_at'])


class QuoteQuestionCommands:
    @staticmethod
    @transaction.atomic
    def create_question(**data) -> QuoteQuestion:
        return QuoteQuestion.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_question(question: QuoteQuestion, data: dict) -> QuoteQuestion:
        for field, value in data.items():
            setattr(question, field, value)
        question.save()
        return question

    @staticmethod
    @transaction.atomic
    def delete_question(question: QuoteQuestion) -> None:
        question.is_deleted = True
        question.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def duplicate_to_module(question: QuoteQuestion, target_module) -> QuoteQuestion:
        """
        Copia (no comparte por referencia) una pregunta + sus opciones a
        otro modulo -- puede ser de otra plantilla. Biblioteca de preguntas
        reutilizable, Fase C de PLAN_MAESTRO_QUOTES_UX.md.

        A diferencia de duplicate_module (que siempre crea un modulo nuevo,
        por lo que el mismo `key` nunca colisiona), aqui el modulo destino
        puede ya existir y ya tener una pregunta con el mismo `key` -- se
        desambigua con un sufijo numerico antes de crear la copia.
        depends_on_question NUNCA se copia (apuntaria a una pregunta del
        modulo de origen, violando la regla de "mismo modulo").
        """
        key = question.key
        if target_module.questions.filter(key=key, is_deleted=False).exists():
            base_key = key
            n = 2
            while target_module.questions.filter(key=key, is_deleted=False).exists():
                key = f"{base_key}_{n}"
                n += 1

        new_question = QuoteQuestion.objects.create(
            module=target_module,
            key=key,
            question_type=question.question_type,
            label=question.label,
            description=question.description,
            help_text=question.help_text,
            placeholder=question.placeholder,
            is_required=question.is_required,
            is_visible=question.is_visible,
            default_value=question.default_value,
            unit=question.unit,
            group=question.group,
            min_value=question.min_value,
            max_value=question.max_value,
            validation_regex=question.validation_regex,
            table_columns=question.table_columns,
            display_order=question.display_order,
            is_active=question.is_active,
            allow_other=question.allow_other,
        )
        for option in question.options.filter(is_deleted=False):
            QuoteQuestionOption.objects.create(
                question=new_question, label=option.label, value=option.value,
                display_order=option.display_order, is_active=option.is_active,
            )
        return new_question


class QuoteQuestionOptionCommands:
    @staticmethod
    @transaction.atomic
    def create_option(option: "QuoteQuestionOption" = None, **data) -> "QuoteQuestionOption":
        from quotes.models import QuoteQuestionOption
        return QuoteQuestionOption.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update_option(option, data: dict):
        from quotes.models import QuoteQuestionOption
        ALLOWED = {'label', 'value', 'position', 'is_active', 'metadata'}
        for k, v in data.items():
            if k in ALLOWED:
                setattr(option, k, v)
        option.save()
        return option

    @staticmethod
    @transaction.atomic
    def delete_option(option) -> None:
        option.is_deleted = True
        option.save(update_fields=['is_deleted', 'updated_at'])
