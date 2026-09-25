import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_baseline_revisions(apps, schema_editor):
    """Version 1 de lo que ya existe: sin esto no habria a que version volver antes del primer cambio. Sin secretos."""
    Config = apps.get_model('ai_provider', 'AIChannelConfig')
    Provider = apps.get_model('ai_provider', 'AIProvider')
    Revision = apps.get_model('ai_provider', 'AIConfigRevision')
    for cfg in Config.objects.filter(is_deleted=False):
        fallbacks = list(cfg.fallbacks.filter(is_deleted=False).select_related('model__provider').order_by('order'))
        labels = {}
        if cfg.primary_model_id:
            labels[str(cfg.primary_model.uuid)] = f'{cfg.primary_model.provider.name} / {cfg.primary_model.model_id}'
        for fb in fallbacks:
            labels[str(fb.model.uuid)] = f'{fb.model.provider.name} / {fb.model.model_id}'
        Revision.objects.create(
            scope='channel', target_uuid=cfg.uuid, channel=cfg.channel, version=1, action='baseline',
            snapshot={
                'enabled': cfg.enabled,
                'primary_model_uuid': str(cfg.primary_model.uuid) if cfg.primary_model_id else None,
                'fallback_model_uuids': [str(fb.model.uuid) for fb in fallbacks],
                'overrides': {'temperature': cfg.temperature, 'max_tokens': cfg.max_tokens, 'timeout': cfg.timeout},
                'labels': labels,
            },
        )
    for prov in Provider.objects.filter(is_deleted=False):
        Revision.objects.create(
            scope='provider', target_uuid=prov.uuid, version=1, action='baseline',
            snapshot={
                'name': prov.name, 'kind': prov.kind, 'base_url': prov.base_url, 'is_active': prov.is_active,
                'display_order': prov.display_order, 'timeout': prov.timeout, 'max_retries': prov.max_retries,
                'metadata': prov.metadata, 'has_api_key': bool(prov.api_key),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_provider', '0006_alter_aichannelconfig_channel'),
    ]

    operations = [
        migrations.AddField(
            model_name='aichannelconfig',
            name='config_version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='aiprovider',
            name='config_version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.CreateModel(
            name='AIConfigRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('scope', models.CharField(choices=[('channel', 'Canal'), ('provider', 'Proveedor')], max_length=20)),
                ('target_uuid', models.UUIDField(db_index=True)),
                ('channel', models.CharField(blank=True, max_length=50)),
                ('version', models.PositiveIntegerField()),
                ('action', models.CharField(max_length=60)),
                ('snapshot', models.JSONField(default=dict)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-version', '-created_at'],
                'constraints': [models.UniqueConstraint(fields=('scope', 'target_uuid', 'version'), name='unique_revision_version_per_target')],
            },
        ),
        migrations.RunPython(create_baseline_revisions, migrations.RunPython.noop),
    ]
