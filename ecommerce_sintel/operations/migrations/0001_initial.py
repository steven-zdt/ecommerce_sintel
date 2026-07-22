import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0004_professionalavailability'),
        ('orders', '0001_initial'),
        ('renting', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DispatcherProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('dispatcher_type', models.CharField(choices=[('DRIVER', 'Conductor'), ('LOGISTICS', 'Logistica'), ('FIELD_OPS', 'Operario de campo')], default='DRIVER', max_length=20)),
                ('vehicle_plate', models.CharField(blank=True, default='', max_length=20)),
                ('vehicle_type', models.CharField(blank=True, default='', max_length=50)),
                ('coverage_cities', models.JSONField(blank=True, default=list)),
                ('is_available', models.BooleanField(db_index=True, default=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dispatcher_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'perfil de despachador',
                'verbose_name_plural': 'perfiles de despachadores',
            },
        ),
        migrations.CreateModel(
            name='OperationTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('ticket_number', models.CharField(db_index=True, max_length=30, unique=True)),
                ('operation_type', models.CharField(choices=[('SHOP_DELIVERY', 'Entrega de tienda'), ('RENTAL', 'Alquiler de equipo'), ('SERVICE', 'Servicio tecnico')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('CREATED', 'Creado'), ('DOCS_PENDING', 'Documentos pendientes'), ('READY_TO_ASSIGN', 'Listo para asignar'), ('ASSIGNED', 'Asignado'), ('SCHEDULED', 'Programado'), ('EN_ROUTE', 'En camino'), ('IN_PROGRESS', 'En ejecucion'), ('COMPLETED', 'Completado'), ('CANCELLED', 'Cancelado')], db_index=True, default='CREATED', max_length=20)),
                ('priority', models.CharField(choices=[('HIGH', 'Alta'), ('LOW', 'Baja')], db_index=True, default='LOW', max_length=10)),
                ('scheduled_date', models.DateField(blank=True, db_index=True, null=True)),
                ('scheduled_time_start', models.TimeField(blank=True, null=True)),
                ('scheduled_time_end', models.TimeField(blank=True, null=True)),
                ('location_address', models.CharField(blank=True, default='', max_length=300)),
                ('location_city', models.CharField(blank=True, default='', max_length=100)),
                ('location_department', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operation_tickets', to=settings.AUTH_USER_MODEL)),
                ('source_order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='operation_ticket', to='orders.order')),
                ('source_rental_request', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='operation_ticket', to='renting.rentalrequest')),
            ],
            options={
                'verbose_name': 'ticket de operacion',
                'verbose_name_plural': 'tickets de operacion',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='operationticket',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(source_order__isnull=False, source_rental_request__isnull=True) |
                    models.Q(source_order__isnull=True, source_rental_request__isnull=False)
                ),
                name='operationticket_single_source',
            ),
        ),
        migrations.CreateModel(
            name='OperationAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('role', models.CharField(choices=[('TECHNICIAN', 'Tecnico'), ('DISPATCHER', 'Despachador')], max_length=15)),
                ('status', models.CharField(choices=[('ACTIVE', 'Activa'), ('RELEASED', 'Liberada')], default='ACTIVE', max_length=10)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='operations.operationticket')),
                ('assignee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operation_assignments', to=settings.AUTH_USER_MODEL)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operation_assignments_made', to=settings.AUTH_USER_MODEL)),
                ('availability_slot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operation_assignments', to='accounts.professionalavailability')),
            ],
            options={
                'verbose_name': 'asignacion de operacion',
                'verbose_name_plural': 'asignaciones de operacion',
            },
        ),
        migrations.CreateModel(
            name='TrackingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('milestone', models.CharField(choices=[('CREATED', 'Solicitud creada'), ('DOCS_APPROVED', 'Documentos aprobados'), ('ASSIGNED', 'Recurso asignado'), ('SCHEDULED', 'Fecha y hora programada'), ('EN_ROUTE', 'En camino'), ('IN_PROGRESS', 'En ejecucion'), ('COMPLETED', 'Completado'), ('CANCELLED', 'Cancelado'), ('NOTE', 'Nota')], db_index=True, max_length=20)),
                ('description', models.TextField(blank=True, default='')),
                ('is_customer_visible', models.BooleanField(default=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_events', to='operations.operationticket')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'evento de tracking',
                'verbose_name_plural': 'eventos de tracking',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='OperationDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('doc_type', models.CharField(choices=[('ID_CARD', 'Cedula de identidad'), ('RENTAL_CONTRACT', 'Contrato de alquiler'), ('SERVICE_CONTRACT', 'Contrato de servicios'), ('INVOICE', 'Factura de compra'), ('OTHER', 'Otro')], db_index=True, max_length=25)),
                ('file', models.FileField(blank=True, null=True, upload_to='operations/documents/%Y/%m/')),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('APPROVED', 'Aprobado'), ('REJECTED', 'Rechazado')], db_index=True, default='PENDING', max_length=10)),
                ('rejection_reason', models.CharField(blank=True, default='', max_length=300)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='operations.operationticket')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_operation_docs', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_operation_docs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'documento de operacion',
                'verbose_name_plural': 'documentos de operacion',
            },
        ),
        migrations.CreateModel(
            name='OperationReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('rating', models.PositiveSmallIntegerField(default=5)),
                ('quality_rating', models.PositiveSmallIntegerField(default=5)),
                ('punctuality_rating', models.PositiveSmallIntegerField(default=5)),
                ('condition_rating', models.PositiveSmallIntegerField(default=5)),
                ('comment', models.TextField(blank=True, default='')),
                ('ticket', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review', to='operations.operationticket')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operation_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'resena de operacion',
                'verbose_name_plural': 'resenas de operacion',
            },
        ),
    ]
