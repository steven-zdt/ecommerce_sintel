from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_homecard_media'),
    ]

    operations = [
        migrations.CreateModel(
            name='FooterLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('title', models.CharField(max_length=100)),
                ('url', models.CharField(max_length=500)),
                ('category', models.CharField(
                    choices=[('social', 'Red Social'), ('nav', 'Navegacion')],
                    db_index=True, default='nav', max_length=10,
                )),
                ('group_name', models.CharField(blank=True, default='', max_length=80)),
                ('icon_class', models.CharField(blank=True, default='', max_length=80)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'enlace del footer',
                'verbose_name_plural': 'enlaces del footer',
                'ordering': ['category', 'group_name', 'display_order'],
            },
        ),
        migrations.CreateModel(
            name='CompanyContactInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('phone', models.CharField(blank=True, default='', max_length=60)),
                ('email', models.CharField(blank=True, default='', max_length=150)),
                ('address', models.CharField(blank=True, default='', max_length=300)),
                ('working_hours', models.CharField(blank=True, default='', max_length=150)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'informacion de contacto',
                'verbose_name_plural': 'informacion de contacto',
                'ordering': ['-is_active', '-created_at'],
            },
        ),
    ]
