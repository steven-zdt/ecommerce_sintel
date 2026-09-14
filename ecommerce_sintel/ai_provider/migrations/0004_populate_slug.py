"""Plan "AI Provider Runtime" FASE 2: poblar `slug` en filas existentes antes de
exigir unicidad (0005). Incluye soft-deleted -- evita colisiones con la
constraint unica al reactivar/reusar nombres."""
from django.db import migrations
from django.utils.text import slugify


def populate_slug(apps, schema_editor):
    AIProvider = apps.get_model('ai_provider', 'AIProvider')
    seen = set()
    for provider in AIProvider.objects.all().order_by('created_at'):
        base = slugify(provider.name) or 'provider'
        slug = base
        n = 1
        while slug in seen or AIProvider.objects.exclude(pk=provider.pk).filter(slug=slug).exists():
            n += 1
            slug = f'{base}-{n}'
        seen.add(slug)
        provider.slug = slug
        provider.save(update_fields=['slug'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ai_provider', '0003_aichannelconfig_enabled_aichannelconfig_max_tokens_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_slug, noop_reverse),
    ]
