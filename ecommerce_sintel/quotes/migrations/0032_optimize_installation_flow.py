from django.db import migrations

TEMPLATE_SLUG = "instalacion-cctv"
INSTALLATION_GROUP = "Informacion de la Instalacion"
DOCUMENT_GROUP = "Documentacion Adjunta"

COLOMBIA_CITIES = [
    "Acacías", "Aguachica", "Aguazul", "Arauca", "Arauquita", "Armenia",
    "Barrancabermeja", "Barranquilla", "Bello", "Bogotá, D.C.", "Bosconia",
    "Bucaramanga", "Buenaventura", "Buga", "Cajicá", "Calarcá", "Caldas",
    "Cali", "Cartagena de Indias", "Cartago", "Cereté", "Chaparral", "Chía",
    "Chinchiná", "Chiquinquirá", "Ciénaga", "Copacabana", "Corozal", "Cúcuta",
    "Dosquebradas", "Duitama", "El Carmen de Bolívar", "Envigado", "Espinal",
    "Facatativá", "Florencia", "Floridablanca", "Fundación", "Funza",
    "Fusagasugá", "Galapa", "Garzón", "Girardot", "Girón", "Granada", "Honda",
    "Ibagué", "Inírida", "Ipiales", "Istmina", "Itagüí", "Jamundí",
    "La Dorada", "La Estrella", "La Paz", "La Plata", "La Virginia",
    "Leticia", "Lorica", "Los Patios", "Madrid", "Magangué", "Maicao",
    "Malambo", "Manaure", "Manizales", "Medellín", "Melgar", "Mitú", "Mocoa",
    "Mompox", "Montenegro", "Montería", "Mosquera", "Neiva", "Ocaña",
    "Orito", "Paipa", "Palmira", "Pamplona", "Pasto", "Pereira",
    "Piedecuesta", "Pitalito", "Plato", "Popayán", "Providencia",
    "Puerto Asís", "Puerto Carreño", "Puerto Colombia", "Puerto López",
    "Puerto Nariño", "Puerto Tejada", "Quibdó", "Quimbaya", "Riohacha",
    "Rionegro", "Riosucio", "Sabanalarga", "Sabaneta", "Sampués",
    "San Andrés", "San Gil", "San José del Guaviare", "San Marcos",
    "San Martín", "San Vicente del Caguán", "Santa Marta",
    "Santa Rosa de Cabal", "Santander de Quilichao", "Saravena", "Sincelejo",
    "Soacha", "Sogamoso", "Soledad", "Tame", "Tauramena", "Tierralta",
    "Tuluá", "Tumaco", "Tunja", "Túquerres", "Turbaco", "Uribia",
    "Valle del Guamuez", "Valledupar", "Villa del Rosario", "Villanueva",
    "Villavicencio", "Yopal", "Yumbo", "Zipaquirá",
]

MATERIALS_MODULE_UUID = "ca7d3530-f228-4baa-a434-5ed35d3e8428"
EQUIPMENT_MODULE_UUID = "a914c992-7c7b-4cb8-b712-29d72b3797da"
MATERIALS_MODULE_NEW_NAME = "Informacion del Proyecto"

# Reordena las preguntas existentes del modulo de instalacion + inserta
# ciudad/direccion antes de compartir ubicacion GPS.
MATERIALS_REORDER = {
    "farthest_equipment_distance": 1,
    "nearest_equipment_distance": 2,
    "installation_environment": 3,
    "project_type": 4,
    "project_location": 7,
    "project_address": 8,
    "existing_infrastructure": 9,
}

NEW_MATERIALS_QUESTIONS = [
    {
        "key": "installation_city", "question_type": "SELECT",
        "label": "Ciudad de la instalacion",
        "help_text": "¿En que ciudad se realizara la instalacion?",
        "is_required": False, "display_order": 5,
        "options": COLOMBIA_CITIES,
    },
    {
        "key": "installation_address", "question_type": "TEXT",
        "label": "Direccion de la instalacion",
        "help_text": "¿Cual es la direccion donde se realizara la instalacion?",
        "is_required": False, "display_order": 6,
    },
]

NEW_EQUIPMENT_QUESTIONS = [
    {
        "key": "has_requirement_document", "question_type": "RADIO",
        "label": "¿Ya tienes un documento con los requerimientos?",
        "help_text": (
            "Si ya tienes un documento con las especificaciones tecnicas, pliego "
            "de condiciones, lista de requerimientos o cualquier informacion "
            "relacionada con la instalacion, puedes adjuntarlo aqui. Nuestro "
            "equipo utilizara esta informacion para complementar el analisis "
            "de tu solicitud."
        ),
        "is_required": False, "display_order": 0,
        "options": ["Si, deseo adjuntar un documento.", "No, continuare diligenciando el formulario."],
    },
    {
        "key": "requirement_documents", "question_type": "FILE",
        "label": "Documentos de requerimientos",
        "help_text": "PDF, DOC, DOCX, XLS, XLSX o TXT -- maximo 20 MB por archivo.",
        "is_required": False, "display_order": 1,
        "depends_on_key": "has_requirement_document",
        "depends_on_values": ["Si, deseo adjuntar un documento."],
    },
]


def optimize_flow(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")
    QuoteQuestionOption = apps.get_model("quotes", "QuoteQuestionOption")

    template = QuoteTemplate.objects.filter(slug=TEMPLATE_SLUG, is_deleted=False).first()
    if not template:
        return

    materials_module = QuoteTemplateModule.objects.filter(uuid=MATERIALS_MODULE_UUID).first()
    equipment_module = QuoteTemplateModule.objects.filter(uuid=EQUIPMENT_MODULE_UUID).first()

    # --- FASE 4: renombrar el modulo, reordenar, agregar ciudad/direccion ---
    if materials_module:
        materials_module.name = MATERIALS_MODULE_NEW_NAME
        materials_module.save(update_fields=["name"])

        for key, order in MATERIALS_REORDER.items():
            QuoteQuestion.objects.filter(module=materials_module, key=key).update(display_order=order)

        for spec in NEW_MATERIALS_QUESTIONS:
            spec = dict(spec)
            options = spec.pop("options", None)
            question, _ = QuoteQuestion.objects.get_or_create(
                module=materials_module, key=spec["key"],
                defaults={**spec, "group": INSTALLATION_GROUP},
            )
            if options and not question.options.exists():
                for i, label in enumerate(options):
                    QuoteQuestionOption.objects.create(
                        question=question, label=label, value=label, display_order=i,
                    )

    # --- FASE 5: eliminar altura duplicada, agregar bloque de documento ---
    if equipment_module:
        QuoteQuestion.objects.filter(module=equipment_module, key="height").delete()

        # Las preguntas de documento deben aparecer primero (display_order es
        # PositiveIntegerField, no admite negativos) -- se empujan las demas.
        QuoteQuestion.objects.filter(module=equipment_module, key="tipo_de_inmueble").update(display_order=10)
        QuoteQuestion.objects.filter(module=equipment_module, key="camera_count").update(display_order=11)

        created_by_key = {}
        pending_deps = []
        for spec in NEW_EQUIPMENT_QUESTIONS:
            spec = dict(spec)
            options = spec.pop("options", None)
            depends_on_key = spec.pop("depends_on_key", None)
            question, _ = QuoteQuestion.objects.get_or_create(
                module=equipment_module, key=spec["key"],
                defaults={**spec, "group": DOCUMENT_GROUP},
            )
            created_by_key[spec["key"]] = question
            if options and not question.options.exists():
                for i, label in enumerate(options):
                    QuoteQuestionOption.objects.create(
                        question=question, label=label, value=label, display_order=i,
                    )
            if depends_on_key:
                pending_deps.append((question, depends_on_key))

        for question, depends_on_key in pending_deps:
            parent = created_by_key.get(depends_on_key)
            if parent and not question.depends_on_question_id:
                question.depends_on_question = parent
                question.save(update_fields=["depends_on_question"])


def revert_flow(apps, schema_editor):
    QuoteTemplateModule = apps.get_model("quotes", "QuoteTemplateModule")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")

    materials_module = QuoteTemplateModule.objects.filter(uuid=MATERIALS_MODULE_UUID).first()
    if materials_module:
        materials_module.name = "Cableado"
        materials_module.save(update_fields=["name"])
        QuoteQuestion.objects.filter(
            module=materials_module, key__in=["installation_city", "installation_address"],
        ).delete()

    equipment_module = QuoteTemplateModule.objects.filter(uuid=EQUIPMENT_MODULE_UUID).first()
    if equipment_module:
        QuoteQuestion.objects.filter(
            module=equipment_module, key__in=["has_requirement_document", "requirement_documents"],
        ).delete()
        QuoteQuestion.objects.get_or_create(
            module=equipment_module, key="height",
            defaults={
                "question_type": "NUMBER", "label": "Altura de instalacion (m)",
                "is_required": False, "display_order": 0,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0031_attachment_filefield"),
    ]

    operations = [migrations.RunPython(optimize_flow, reverse_code=revert_flow)]
