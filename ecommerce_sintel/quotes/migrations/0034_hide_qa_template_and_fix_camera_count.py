from django.db import migrations

QA_TEMPLATE_SLUG = "instalacion-cctv-qa"


def hide_qa_and_fix_camera_count(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")

    # H5: la plantilla de QA no debe ser visible/seleccionable en /cotizar,
    # sin importar que alguien vuelva a marcar is_published=True por error
    # -- is_internal es la barrera definitiva (ver selectors.py).
    QuoteTemplate.objects.filter(slug=QA_TEMPLATE_SLUG).update(
        is_published=False, is_internal=True,
    )

    # H4: camera_count (Cantidad de Equipos) era la unica pregunta NUMBER
    # obligatoria de la plantilla real sin min/max -- permitia valores
    # negativos o absurdos (ver auditoria E2E 2026-07-23).
    QuoteQuestion.objects.filter(
        module__template__slug="instalacion-cctv", key="camera_count",
    ).update(min_value=1, max_value=5000, placeholder="Ejemplo: 8")


def reverse(apps, schema_editor):
    QuoteTemplate = apps.get_model("quotes", "QuoteTemplate")
    QuoteQuestion = apps.get_model("quotes", "QuoteQuestion")
    QuoteTemplate.objects.filter(slug=QA_TEMPLATE_SLUG).update(
        is_published=True, is_internal=False,
    )
    QuoteQuestion.objects.filter(
        module__template__slug="instalacion-cctv", key="camera_count",
    ).update(min_value=None, max_value=None, placeholder="")


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0033_add_is_internal_flag"),
    ]

    operations = [migrations.RunPython(hide_qa_and_fix_camera_count, reverse_code=reverse)]
