from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('renting', '0009_rentalrequest_priority'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RentalProjectAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('file', models.FileField(upload_to='renting/project_attachments/%Y/%m/')),
                ('original_name', models.CharField(blank=True, default='', max_length=255)),
                ('content_type', models.CharField(blank=True, default='', max_length=100)),
                ('rental_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_attachments', to='renting.rentalrequest')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rental_project_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
