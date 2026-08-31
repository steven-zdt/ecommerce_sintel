# Hand-written (FASE 6, integracion Meta Business, 2026-08-31). Equivalente a lo
# que produce `makemigrations notifications` para el modelo MetaWebhookEvent
# nuevo en notifications/models.py -- verificar con
# `docker compose exec django python manage.py makemigrations notifications --check`.
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0007_notificationlog_notificatio_templat_6766a7_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MetaWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('object_type', models.CharField(choices=[('whatsapp_business_account', 'WhatsApp Business Account'), ('page', 'Facebook Page'), ('instagram', 'Instagram'), ('unknown', 'Desconocido')], db_index=True, default='unknown', max_length=32)),
                ('event_type', models.CharField(blank=True, default='', help_text="'messages', 'message_status', 'statuses', ...", max_length=64)),
                ('business_id', models.CharField(blank=True, default='', max_length=64)),
                ('waba_id', models.CharField(blank=True, default='', max_length=64)),
                ('phone_number_id', models.CharField(blank=True, default='', max_length=64)),
                ('external_message_id', models.CharField(blank=True, db_index=True, default='', help_text='ID del mensaje asignado por Meta (wamid...), cuando aplica.', max_length=255)),
                ('payload_hash', models.CharField(blank=True, db_index=True, default='', help_text='SHA-256 del cuerpo crudo del webhook. Dedupe + deteccion de manipulacion.', max_length=64)),
                ('signature_valid', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('RECEIVED', 'Recibido'), ('PROCESSING', 'En proceso'), ('PROCESSED', 'Procesado'), ('FAILED', 'Fallido'), ('DUPLICATE', 'Duplicado (reintento de Meta)'), ('REJECTED', 'Rechazado (firma invalida)')], db_index=True, default='RECEIVED', max_length=12)),
                ('received_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('retry_count', models.PositiveSmallIntegerField(default=0)),
                ('error_code', models.CharField(blank=True, default='', max_length=64)),
                ('payload', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'verbose_name': 'Evento de webhook Meta',
                'verbose_name_plural': 'Eventos de webhook Meta',
                'ordering': ['-received_at'],
            },
        ),
        migrations.AddIndex(
            model_name='metawebhookevent',
            index=models.Index(fields=['object_type', 'status'], name='notificatio_object__922ad6_idx'),
        ),
        migrations.AddIndex(
            model_name='metawebhookevent',
            index=models.Index(fields=['status', 'received_at'], name='notificatio_status_7e1180_idx'),
        ),
    ]
