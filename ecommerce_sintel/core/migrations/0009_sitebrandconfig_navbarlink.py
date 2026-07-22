import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_homemoduleconfig_background_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteBrandConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('site_name', models.CharField(default='Sintel', max_length=100)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='brand/')),
                ('tagline', models.CharField(blank=True, default='', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'configuracion de marca',
                'verbose_name_plural': 'configuracion de marca',
            },
        ),
        migrations.CreateModel(
            name='NavbarLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('label', models.CharField(max_length=80)),
                ('url', models.CharField(max_length=200)),
                ('icon_class', models.CharField(blank=True, default='', max_length=80)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('is_visible', models.BooleanField(db_index=True, default=True)),
                ('open_in_new_tab', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'enlace del navbar',
                'verbose_name_plural': 'enlaces del navbar',
                'ordering': ['display_order'],
            },
        ),
    ]
