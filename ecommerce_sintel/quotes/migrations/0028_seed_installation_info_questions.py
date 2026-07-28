from django.db import migrations

TEMPLATE_SLUG = "instalacion-cctv"
GROUP_LABEL = "Informacion de la Instalacion"

# key -> (label, help_text/placeholder/etc via kwargs)
QUESTIONS = [
    {
        "key": "farthest_equipment_distance",
        "question_type": "NUMBER",
        "label": "Distancia del equipo mas lejano",
        "help_text": "¿Cuantos metros aproximadamente hay desde el punto principal de instalacion hasta el equipo mas lejano?",
        "placeholder": "Ejemplo: 85",
        "unit": "metros",
        "is_required": True,
        "min_value": 1,
        "max_value": 1000,
        "display_order": 1,
    },
    {
        "key": "nearest_equipment_distance",
        "question_type": "NUMBER",
        "label": "Distancia del equipo mas cercano",
        "help_text": "¿Cuantos metros aproximadamente hay desde el punto principal de instalacion hasta el equipo mas cercano?",
        "placeholder": "Ejemplo: 8",
        "unit": "metros",
        "is_required": False,
        "min_value": 0,
        "max_value": 1000,
        "display_order": 2,
    },
    {
        "key": "installation_environment",
        "question_type": "RADIO",
        "label": "Tipo de instalacion",
        "help_text": "¿Donde se realizara la instalacion?",
        "is_required": False,
        "display_order": 3,
        "options": ["Interior", "Exterior", "Mixta (Interior y Exterior)"],
    },
    {
        "key": "project_type",
        "question_type": "SELECT",
        "label": "Tipo de proyecto",
        "help_text": "¿Para que tipo de instalacion necesitas la cotizacion?",
        "is_required": False,
        "allow_other": True,
        "display_order": 4,
        "options": [
            "Hogar", "Empresa", "Oficina", "Local Comercial", "Retail",
            "Centro Comercial", "Conjunto Residencial", "Edificio", "Hospital",
            "Clinica", "Industria", "Bodega", "Parqueadero", "Hotel",
            "Institucion Educativa", "Entidad Publica",
        ],
    },
    {
        "key": "project_location",
        "question_type": "GPS",
        "label": "Comparte tu ubicacion",
        "help_text": "Comparte la ubicacion aproximada donde se realizara la instalacion.",
        "is_required": False,
        "display_order": 5,
    },
    {
        "key": "project_address",
        "question_type": "ADDRESS",
        "label": "Direccion del proyecto",
        "is_required": False,
        "display_order": 6,
        # Solo se muestra si project_location quedo en 'DENIED' (permiso GPS
        # rechazado o no disponible) -- ver DynamicQuestionField.vue.
        "depends_on_key": "project_location",
        "depends_on_values": ["DENIED"],
    },
    {
        "key": "existing_infrastructure",
        "question_type": "RADIO",
        "label": "¿Existe actualmente infraestructura instalada?",
        "is_required": False,
        "display_order": 7,
        "options": [
            "Si, se puede reutilizar",
            "Si, pero requiere adecuaciones",
            "No existe infraestructura",
            "No estoy seguro",
        ],
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
        template=template, module_type="MATERIALS", is_deleted=False,
    ).order_by("display_order", "id").first()
    if not module:
        return

    created_by_key = {}
    for spec in QUESTIONS:
        options = spec.pop("options", None)
        depends_on_key = spec.pop("depends_on_key", None)
        question, _ = QuoteQuestion.objects.get_or_create(
            module=module, key=spec["key"],
            defaults={**spec, "group": GROUP_LABEL},
        )
        created_by_key[spec["key"]] = question
        if options and not question.options.exists():
            for i, label in enumerate(options):
                QuoteQuestionOption.objects.create(
                    question=question, label=label, value=label, display_order=i,
                )

    address_q = created_by_key.get("project_address")
    location_q = created_by_key.get("project_location")
    if address_q and location_q and not address_q.depends_on_question_id:
        address_q.depends_on_question = location_q
        address_q.save(update_fields=["depends_on_question"])


def remove_questions(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")

    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG).first()
    if not template:
        return
    module = QuoteTemplateModule.objects.filter(template=template, module_type="MATERIALS").first()
    if not module:
        return
    QuoteQuestion.objects.filter(
        module=module, key__in=[q["key"] for q in QUESTIONS] + ["project_address"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0027_seed_notify_quotations_periodic_task"),
    ]

    operations = [migrations.RunPython(seed_questions, reverse_code=remove_questions)]
