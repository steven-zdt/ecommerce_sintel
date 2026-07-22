from django.db import migrations, models

STATUS_CHOICES = [
    ('BORRADOR', 'Borrador'), ('RECIBIDA', 'Recibida'), ('EN_REVISION', 'En revision'),
    ('PENDIENTE_INFORMACION', 'Pendiente informacion'), ('COTIZADA', 'Cotizada'),
    ('ENVIADA', 'Enviada'), ('ACEPTADA', 'Aceptada'), ('RECHAZADA', 'Rechazada'),
    ('VENCIDA', 'Vencida'), ('CANCELADA', 'Cancelada'),
]

STATUS_REMAP = {
    'DRAFT': 'BORRADOR',
    'SENT': 'ENVIADA',
    'ACCEPTED': 'ACEPTADA',
    'REJECTED': 'RECHAZADA',
    'EXPIRED': 'VENCIDA',
}


def remap_status_forward(apps, schema_editor):
    Quotation = apps.get_model('quotes', 'Quotation')
    for old, new in STATUS_REMAP.items():
        Quotation.objects.filter(status=old).update(status=new)


def remap_status_backward(apps, schema_editor):
    Quotation = apps.get_model('quotes', 'Quotation')
    for old, new in STATUS_REMAP.items():
        Quotation.objects.filter(status=new).update(status=old)


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0017_remove_calc_engine_models'),
    ]

    operations = [
        migrations.RunPython(remap_status_forward, remap_status_backward),
        migrations.AlterField(
            model_name='quotation',
            name='status',
            field=models.CharField(choices=STATUS_CHOICES, default='BORRADOR', max_length=25),
        ),
        migrations.RemoveField(
            model_name='quotation',
            name='generated_summary',
        ),
        migrations.AlterField(
            model_name='quotation',
            name='answers',
            field=models.JSONField(blank=True, default=dict, help_text='Respuestas del cliente organizadas por modulo: {"<module_uuid>": {"<question_key>": valor}}.'),
        ),
        migrations.AddField(
            model_name='quotationattachment',
            name='note',
            field=models.CharField(blank=True, default='', help_text="Contexto del adjunto, ej. 'module_uuid:question_key' para respuestas de preguntas tipo archivo.", max_length=255),
        ),
    ]
