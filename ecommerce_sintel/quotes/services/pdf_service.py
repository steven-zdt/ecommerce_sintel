import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

_DARK = colors.HexColor('#2c3e50')
_ACCENT = colors.HexColor('#1a6fa8')
_LIGHT = colors.HexColor('#ecf0f1')


def _resolve_answer_display(question, value):
    """
    Equivalente Python de resolveQuestionLabel (H3, auditoria E2E 2026-07-23,
    ver frontend/src/utils/formatQuoteAnswer.js) -- mismo criterio: si la
    pregunta es SELECT/RADIO/MULTISELECT/CHECKBOX, resuelve el valor crudo
    contra sus QuoteQuestionOption para mostrar el label (ej. 'edificio' ->
    'Edificio') en vez del valor almacenado. GPS: 'DENIED' es el sentinela de
    permiso rechazado (ver DynamicQuestionField.vue), no una QuoteQuestionOption.
    """
    if value == 'DENIED':
        return 'No compartida (direccion manual)'
    if isinstance(value, dict) and 'lat' in value and 'lng' in value:
        return f"{value['lat']:.5f}, {value['lng']:.5f}"
    options = {opt.value: opt.label for opt in question.options.all()} if hasattr(question, 'options') else {}
    if isinstance(value, list):
        return ', '.join(str(options.get(v, v)) for v in value)
    return str(options.get(value, value))


class PDFService:
    @staticmethod
    def generate_quotation_pdf(quotation) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'],
            fontSize=18, alignment=TA_CENTER, spaceAfter=6, textColor=_DARK
        )
        sub_style = ParagraphStyle(
            'SubStyle', parent=styles['Normal'],
            fontSize=9, leading=13, textColor=colors.HexColor('#555555')
        )
        section_style = ParagraphStyle(
            'SectionStyle', parent=styles['Heading3'],
            fontSize=11, spaceBefore=14, spaceAfter=6, textColor=_ACCENT
        )
        label_style = ParagraphStyle(
            'LabelStyle', parent=styles['Normal'],
            fontSize=9, leading=12
        )

        col_w = [200, 50, 100, 100]

        def _table_header_style():
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), _DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, _LIGHT]),
            ])

        # Title
        # [2026-07-12] Antes tenia "SINTEL" hardcodeado -- unico caso encontrado en la
        # auditoria de MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md donde el nombre de la
        # empresa vivia fuera de una fuente centralizada. Ahora lee organization.Company
        # (SSoT), con "Sintel" como fallback si todavia no hay una fila activa.
        from organization.services.selectors import OrganizationSelector
        company = OrganizationSelector.get_company()
        trade_name = company.trade_name if company else 'Sintel'
        # H2 (auditoria E2E 2026-07-23): titulo por modo -- "Solicitud" (sin
        # precios, el asesor aun no coteizo) vs "Cotizacion" (ya tiene items o
        # servicios con precio). has_priced_items se calcula un poco mas abajo
        # antes de necesitarse aqui tambien.
        has_priced_items = (
            quotation.items.filter(is_deleted=False).exists()
            or quotation.services.filter(is_deleted=False).exists()
            or quotation.rental_items.filter(is_deleted=False).exists()
        )
        title_text = (
            f"PRESUPUESTO COMERCIAL - {trade_name.upper()}" if has_priced_items
            else f"SOLICITUD DE COTIZACION - {trade_name.upper()}"
        )
        elements.append(Paragraph(title_text, title_style))
        if quotation.template_id:
            badge = f"Plantilla: {quotation.template.name}"
        else:
            badge = "PERSONALIZADO" if quotation.is_custom else "ESTANDAR"
        elements.append(Paragraph(f"Tipo: {badge}", sub_style))
        elements.append(Spacer(1, 10))

        # Client Info
        elements.append(Paragraph(f"<b>Cliente:</b> {quotation.client_name}", label_style))
        elements.append(Paragraph(f"<b>Email:</b> {quotation.client_email}", label_style))
        if quotation.company:
            elements.append(Paragraph(f"<b>Empresa:</b> {quotation.company}", label_style))
        if quotation.phone:
            elements.append(Paragraph(f"<b>Telefono:</b> {quotation.phone}", label_style))
        if quotation.city or quotation.address:
            elements.append(Paragraph(f"<b>Ubicacion:</b> {quotation.address} {quotation.city} {quotation.department}", label_style))
        elements.append(Paragraph(f"<b>Fecha:</b> {quotation.created_at.strftime('%Y-%m-%d')}", label_style))
        elements.append(Paragraph(f"<b>Vence:</b> {quotation.valid_until.strftime('%Y-%m-%d')}", label_style))
        elements.append(Paragraph(f"<b>Estado:</b> {quotation.get_status_display()}", label_style))
        elements.append(Spacer(1, 16))

        # --- Requerimiento capturado por el cuestionario tecnico ---
        # Se muestra mientras la solicitud aun no tiene items/servicios con
        # precio (el asesor todavia no la cotizo). Una vez cotizada, las
        # secciones de Productos/Servicios de mas abajo ya cubren el precio
        # y este resumen de respuestas se omite para no duplicar el PDF.
        if quotation.template_id and not has_priced_items:
            module_order = {'EQUIPMENT': 0, 'MATERIALS': 1, 'LABOR': 2}
            modules = sorted(
                quotation.template.modules.filter(is_deleted=False).prefetch_related('questions', 'questions__options'),
                key=lambda m: (module_order.get(m.module_type, 9), m.display_order),
            )
            answers = quotation.answers or {}
            elements.append(Paragraph("REQUERIMIENTO DEL CLIENTE", section_style))
            for module in modules:
                module_answers = answers.get(str(module.uuid)) or {}
                questions = [q for q in module.questions.all() if not q.is_deleted]
                rows = [
                    [q.label, _resolve_answer_display(q, module_answers[q.key])]
                    for q in sorted(questions, key=lambda q: q.display_order)
                    if q.key in module_answers
                ]
                if not rows:
                    continue
                elements.append(Paragraph(module.get_module_type_display(), label_style))
                q_table = Table([["Pregunta", "Respuesta"]] + rows, colWidths=[250, 250])
                q_table.setStyle(_table_header_style())
                elements.append(q_table)
                elements.append(Spacer(1, 10))

        # --- Products ---
        if quotation.items.filter(is_deleted=False).exists():
            elements.append(Paragraph("EQUIPOS Y PRODUCTOS", section_style))
            data = [["Producto", "Cant.", "V. Unitario", "Subtotal"]]
            for item in quotation.items.filter(is_deleted=False):
                data.append([
                    item.product_name,
                    str(item.quantity),
                    f"${item.unit_price:,.2f}",
                    f"${item.subtotal:,.2f}",
                ])
            t = Table(data, colWidths=col_w)
            t.setStyle(_table_header_style())
            elements.append(t)
            elements.append(Spacer(1, 12))

        # --- Services ---
        if quotation.services.filter(is_deleted=False).exists():
            elements.append(Paragraph("SERVICIOS TECNICOS", section_style))
            for s in quotation.services.filter(is_deleted=False):
                svc_label = s.service_name
                if s.custom_service_type:
                    svc_label = f"{s.custom_service_type}: {s.service_name}"
                elements.append(Paragraph(f"<b>{svc_label}</b>  |  Horas: {s.hours}", label_style))
                if s.labor_description:
                    elements.append(Paragraph(s.labor_description, sub_style))

                if s.materials.filter(is_deleted=False).exists():
                    m_data = [["Material / Insumo", "Cant.", "V. Unitario", "Subtotal"]]
                    for m in s.materials.filter(is_deleted=False):
                        m_data.append([
                            m.material_name,
                            f"{m.quantity:g}",
                            f"${m.unit_price:,.2f}",
                            f"${m.subtotal:,.2f}",
                        ])
                    mt = Table(m_data, colWidths=col_w)
                    mt.setStyle(_table_header_style())
                    elements.append(mt)

                s_summary = [
                    ["Mano de Obra:", f"${s.labor_cost:,.2f}"],
                    ["Total Insumos:", f"${s.material_cost:,.2f}"],
                    [f"SUBTOTAL {s.service_name}:", f"${s.subtotal:,.2f}"],
                ]
                st = Table(s_summary, colWidths=[350, 100])
                st.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(st)
                elements.append(Spacer(1, 10))

        # --- Rentals ---
        if quotation.rental_items.filter(is_deleted=False).exists():
            elements.append(Paragraph("EQUIPOS EN ALQUILER", section_style))
            r_data = [["Equipo", "Inicio", "Fin", "Dias", "$/dia", "Subtotal"]]
            r_col_w = [160, 65, 65, 40, 80, 80]
            for r in quotation.rental_items.filter(is_deleted=False):
                r_data.append([
                    r.equipment_name,
                    str(r.rent_start_date),
                    str(r.rent_end_date),
                    f"{r.computed_days:g}",
                    f"${r.rental_price_per_day:,.2f}",
                    f"${r.subtotal:,.2f}",
                ])
            rt = Table(r_data, colWidths=r_col_w)
            rt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), _ACCENT),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, _LIGHT]),
            ]))
            elements.append(rt)
            elements.append(Spacer(1, 12))

        # --- Totals ---
        # H2: modo Solicitud no muestra precios/subtotales/TOTAL -- el asesor
        # todavia no coteizo, mostrar "$0.00" aqui era enganoso.
        if has_priced_items:
            total_rows = []
            if quotation.subtotal_products:
                total_rows.append(["Subtotal Equipos:", f"${quotation.subtotal_products:,.2f}"])
            if quotation.subtotal_services:
                total_rows.append(["Subtotal Servicios:", f"${quotation.subtotal_services:,.2f}"])
            if quotation.subtotal_rentals:
                total_rows.append(["Subtotal Alquileres:", f"${quotation.subtotal_rentals:,.2f}"])
            total_rows.append(["TOTAL PRESUPUESTO:", f"${quotation.total_amount:,.2f}"])

            t_total = Table(total_rows, colWidths=[350, 100])
            t_total.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 11),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ]))
            elements.append(t_total)

        if quotation.notes:
            elements.append(Spacer(1, 14))
            elements.append(Paragraph(f"<b>Notas:</b> {quotation.notes}", label_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer
