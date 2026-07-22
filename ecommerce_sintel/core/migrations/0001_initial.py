import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='HomeBanner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('title', models.CharField(max_length=150)),
                ('subtitle', models.CharField(blank=True, default='', max_length=255)),
                ('image', models.ImageField(blank=True, null=True, upload_to='home_banners/')),
                ('link_url', models.CharField(blank=True, default='', max_length=500)),
                ('link_label', models.CharField(blank=True, default='', max_length=80)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
            ],
            options={
                'verbose_name': 'banner de inicio',
                'verbose_name_plural': 'banners de inicio',
                'ordering': ['display_order', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='HomeModuleConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('module_key', models.CharField(
                    choices=[
                        ('shop', 'Tienda'),
                        ('renting', 'Alquiler de Equipos'),
                        ('services', 'Servicios Tecnicos'),
                        ('quotes', 'Cotizaciones'),
                    ],
                    max_length=20,
                    unique=True,
                )),
                ('is_visible', models.BooleanField(db_index=True, default=True)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('featured_items_limit', models.PositiveIntegerField(default=8)),
            ],
            options={
                'verbose_name': 'configuracion de modulo en home',
                'verbose_name_plural': 'configuracion de modulos en home',
                'ordering': ['display_order'],
            },
        ),
        migrations.AddIndex(
            model_name='homebanner',
            index=models.Index(fields=['uuid'], name='core_homebanner_uuid_idx'),
        ),
        migrations.AddIndex(
            model_name='homebanner',
            index=models.Index(fields=['-created_at'], name='core_homebanner_created_idx'),
        ),
        migrations.AddIndex(
            model_name='homemoduleconfig',
            index=models.Index(fields=['uuid'], name='core_homemoduleconfig_uuid_idx'),
        ),
        migrations.AddIndex(
            model_name='homemoduleconfig',
            index=models.Index(fields=['-created_at'], name='core_homemoduleconfig_created_idx'),
        ),
    ]
