import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_timeline(apps, schema_editor):
    Quotation = apps.get_model('quotes', 'Quotation')
    QuotationTimeline = apps.get_model('quotes', 'QuotationTimeline')
    QuotationTimeline.objects.bulk_create([
        QuotationTimeline(quotation=q, status=q.status, notes='Estado inicial migrado.')
        for q in Quotation.objects.filter(is_deleted=False)
    ])


def noop_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0018_quotation_status_rework'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QuotationTimeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('status', models.CharField(choices=[
                    ('BORRADOR', 'Borrador'), ('RECIBIDA', 'Recibida'), ('EN_REVISION', 'En revision'),
                    ('PENDIENTE_INFORMACION', 'Pendiente informacion'), ('COTIZADA', 'Cotizada'),
                    ('ENVIADA', 'Enviada'), ('ACEPTADA', 'Aceptada'), ('RECHAZADA', 'Rechazada'),
                    ('VENCIDA', 'Vencida'), ('CANCELADA', 'Cancelada'),
                ], max_length=25)),
                ('notes', models.TextField(blank=True, default='')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quotation_status_changes', to=settings.AUTH_USER_MODEL)),
                ('quotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_events', to='quotes.quotation')),
            ],
            options={
                'verbose_name': 'Evento de Cotizacion',
                'verbose_name_plural': 'Historial de Cotizacion',
                'ordering': ['created_at'],
            },
        ),
        migrations.RunPython(backfill_timeline, noop_backward),
    ]
