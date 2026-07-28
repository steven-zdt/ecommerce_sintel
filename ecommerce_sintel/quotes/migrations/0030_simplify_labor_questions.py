from django.db import migrations

TEMPLATE_SLUG = "instalacion-cctv"

REMOVED_KEYS = [
    "work_at_height",
    "hsq_requirements",
    "access_equipment",
    "scaffold_height",
    "platform_access_type",
    "site_operation_status",
    "service_shutdown_required",
]

NEW_HEIGHT_HELP_TEXT = (
    "Si la instalacion supera los 2 metros de altura, se considera trabajo "
    "en alturas y el sistema determinara automaticamente las medidas de "
    "seguridad."
)
OLD_HEIGHT_HELP_TEXT = "¿A que altura aproximada se instalaran los equipos?"

# Definiciones originales (migracion 0029) -- solo para poder revertir esta
# migracion sin perder datos si algun entorno hace rollback.
REMOVED_QUESTIONS_ORIGINAL = [
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
        "key": "scaffold_height", "question_type": "NUMBER",
        "label": "Altura estimada del andamio",
        "help_text": "¿Cual es la altura estimada del andamio?",
        "placeholder": "Ejemplo: 3", "unit": "metros",
        "is_required": False, "min_value": 0, "max_value": 100, "display_order": 5,
        "depends_on_key": "access_equipment", "depends_on_values": ["Andamio"],
    },
    {
        "key": "platform_access_type", "question_type": "TEXT",
        "label": "Tipo de plataforma elevadora",
        "help_text": "¿Que tipo de acceso requiere la plataforma elevadora?",
        "placeholder": "Ejemplo: tijera, brazo articulado, autopropulsada...",
        "is_required": False, "display_order": 6,
        "depends_on_key": "access_equipment", "depends_on_values": ["Plataforma Elevadora"],
    },
    {
        "key": "site_operation_status", "question_type": "RADIO",
        "label": "Disponibilidad del sitio",
        "help_text": "¿El lugar permanecera operativo durante la instalacion?",
        "is_required": False, "display_order": 8,
        "options": ["Si", "No", "Parcialmente"],
    },
    {
        "key": "service_shutdown_required", "question_type": "RADIO",
        "label": "Interrupcion del servicio",
        "help_text": "¿La instalacion requiere suspender temporalmente algun servicio?",
        "is_required": False, "display_order": 11,
        "options": ["Si", "No", "No lo se"],
    },
]


def simplify_questions(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")

    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG, is_deleted=False).first()
    if not template:
        return
    module = QuoteTemplateModule.objects.filter(template=template, module_type="LABOR").first()
    if not module:
        return

    QuoteQuestion.objects.filter(module=module, key__in=REMOVED_KEYS).delete()
    QuoteQuestion.objects.filter(module=module, key="installation_height").update(
        help_text=NEW_HEIGHT_HELP_TEXT,
    )


def restore_questions(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")
    QuoteQuestionOption = apps.get_model("quotes", "QuoteQuestionOption")

    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG).first()
    if not template:
        return
    module = QuoteTemplateModule.objects.filter(template=template, module_type="LABOR").first()
    if not module:
        return

    QuoteQuestion.objects.filter(module=module, key="installation_height").update(
        help_text=OLD_HEIGHT_HELP_TEXT,
    )

    created_by_key = {}
    for spec in REMOVED_QUESTIONS_ORIGINAL:
        spec = dict(spec)
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
            parent = created_by_key.get(depends_on_key) or QuoteQuestion.objects.filter(
                module=module, key=depends_on_key,
            ).first()
            if parent and not question.depends_on_question_id:
                question.depends_on_question = parent
                question.save(update_fields=["depends_on_question"])


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0029_seed_labor_questions"),
    ]

    operations = [migrations.RunPython(simplify_questions, reverse_code=restore_questions)]
