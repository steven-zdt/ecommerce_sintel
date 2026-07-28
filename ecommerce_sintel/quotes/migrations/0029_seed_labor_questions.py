from django.db import migrations

TEMPLATE_SLUG = "instalacion-cctv"
MODULE_NAME = "Condiciones de Instalacion"

QUESTIONS = [
    {
        "key": "installation_height", "question_type": "NUMBER",
        "label": "Altura de instalacion",
        "help_text": "¿A que altura aproximada se instalaran los equipos?",
        "placeholder": "Ejemplo: 4", "unit": "metros",
        "is_required": True, "min_value": 0, "max_value": 100, "display_order": 1,
    },
    {
        "key": "work_at_height", "question_type": "RADIO",
        "label": "Trabajo en alturas",
        "help_text": "¿La instalacion requiere trabajo seguro en alturas?",
        "is_required": False, "display_order": 2,
        "options": ["Si", "No", "No estoy seguro"],
    },
    {
        "key": "hsq_requirements", "question_type": "CHECKBOX",
        "label": "Nivel de riesgo HSQ",
        "help_text": "¿Que requisitos de Seguridad y Salud en el Trabajo exige el sitio?",
        "is_required": False, "display_order": 3,
        "options": [
            "Ninguno", "Permiso de trabajo", "Induccion HSEQ", "ARL vigente",
            "Curso de alturas", "Uso obligatorio de EPP", "Supervisor SST",
            "Analisis de Riesgos", "ATS", "Permiso de Energia", "LOTO",
            "No conozco los requisitos",
        ],
    },
    {
        "key": "access_equipment", "question_type": "MULTISELECT",
        "label": "Equipos de acceso requeridos",
        "help_text": "¿Que equipos seran necesarios para realizar la instalacion?",
        "is_required": False, "display_order": 4,
        "options": [
            "Escalera", "Andamio", "Plataforma Elevadora", "Manlift",
            "Canastilla", "Grua", "Ninguno", "No estoy seguro",
        ],
    },
    {
        # Regla 2: si se selecciona Andamio, permitir registrar su altura estimada.
        "key": "scaffold_height", "question_type": "NUMBER",
        "label": "Altura estimada del andamio",
        "help_text": "¿Cual es la altura estimada del andamio?",
        "placeholder": "Ejemplo: 3", "unit": "metros",
        "is_required": False, "min_value": 0, "max_value": 100, "display_order": 5,
        "depends_on_key": "access_equipment", "depends_on_values": ["Andamio"],
    },
    {
        # Regla 3: si se selecciona Plataforma Elevadora, pedir el tipo de acceso.
        "key": "platform_access_type", "question_type": "TEXT",
        "label": "Tipo de plataforma elevadora",
        "help_text": "¿Que tipo de acceso requiere la plataforma elevadora?",
        "placeholder": "Ejemplo: tijera, brazo articulado, autopropulsada...",
        "is_required": False, "display_order": 6,
        "depends_on_key": "access_equipment", "depends_on_values": ["Plataforma Elevadora"],
    },
    {
        "key": "allowed_schedule", "question_type": "MULTISELECT",
        "label": "Horario permitido",
        "help_text": "¿En que horario puede realizarse la instalacion?",
        "is_required": False, "display_order": 7,
        "options": [
            "Horario Diurno", "Horario Nocturno", "Fin de Semana", "Festivos",
            "24 Horas", "Horario Administrativo", "No tengo restriccion",
        ],
    },
    {
        "key": "site_operation_status", "question_type": "RADIO",
        "label": "Disponibilidad del sitio",
        "help_text": "¿El lugar permanecera operativo durante la instalacion?",
        "is_required": False, "display_order": 8,
        "options": ["Si", "No", "Parcialmente"],
    },
    {
        "key": "site_access_requirements", "question_type": "MULTISELECT",
        "label": "Restricciones de ingreso",
        "help_text": "¿Existen restricciones para ingresar al sitio?",
        "is_required": False, "display_order": 9,
        "options": [
            "Registro previo", "Documento de identidad", "Autorizacion previa",
            "Carnet empresarial", "Curso de induccion", "Elementos de proteccion",
            "Vehiculo autorizado", "Ninguna", "No se",
        ],
    },
    {
        "key": "power_available", "question_type": "RADIO",
        "label": "Disponibilidad de energia",
        "help_text": "¿Existe alimentacion electrica disponible en el sitio?",
        "is_required": False, "display_order": 10,
        "options": ["Si", "No", "No estoy seguro"],
    },
    {
        "key": "service_shutdown_required", "question_type": "RADIO",
        "label": "Interrupcion del servicio",
        "help_text": "¿La instalacion requiere suspender temporalmente algun servicio?",
        "is_required": False, "display_order": 11,
        "options": ["Si", "No", "No lo se"],
    },
    {
        "key": "labor_notes", "question_type": "TEXTAREA",
        "label": "Observaciones",
        "help_text": "¿Hay alguna condicion especial que debamos conocer antes de realizar la instalacion?",
        "placeholder": "Ejemplo: El area solo esta disponible despues de las 8:00 p.m.",
        "is_required": False, "display_order": 12,
    },
]


def seed_questions(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")
    QuoteQuestionOption = apps.get_model("quotes", "QuoteQuestionOption")

    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG, is_deleted=False).first()
    if not template:
        return  # entorno sin esta plantilla (ej. instancia nueva) -- no-op seguro

    module = QuoteTemplateModule.objects.filter(
        template=template, module_type="LABOR", is_deleted=False,
    ).order_by("display_order", "id").first()
    if not module:
        module = QuoteTemplateModule.objects.create(
            template=template, module_type="LABOR", name=MODULE_NAME,
            display_order=2,
        )

    created_by_key = {}
    for spec in QUESTIONS:
        options = spec.pop("options", None)
        depends_on_key = spec.pop("depends_on_key", None)
        question, _ = QuoteQuestion.objects.get_or_create(
            module=module, key=spec["key"], defaults=spec,
        )
        created_by_key[spec["key"]] = question
        if options and not question.options.exists():
            for i, label in enumerate(options):
                QuoteQuestionOption.objects.create(
                    question=question, label=label, value=label, display_order=i,
                )
        if depends_on_key:
            spec["_depends_on_key"] = depends_on_key

    for spec in QUESTIONS:
        depends_on_key = spec.get("_depends_on_key")
        if not depends_on_key:
            continue
        question = created_by_key[spec["key"]]
        parent = created_by_key.get(depends_on_key)
        if parent and not question.depends_on_question_id:
            question.depends_on_question = parent
            question.save(update_fields=["depends_on_question"])


def remove_questions(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")
    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG).first()
    if not template:
        return
    module = QuoteTemplateModule.objects.filter(template=template, module_type="LABOR", name=MODULE_NAME).first()
    if not module:
        return
    QuoteQuestion.objects.filter(module=module, key__in=[q["key"] for q in QUESTIONS]).delete()
    if not module.questions.exists():
        module.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0028_seed_installation_info_questions"),
    ]

    operations = [migrations.RunPython(seed_questions, reverse_code=remove_questions)]
