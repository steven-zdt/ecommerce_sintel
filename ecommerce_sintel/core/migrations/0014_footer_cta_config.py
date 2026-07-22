from django.db import migrations, models
import uuid as uuid_lib


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_homebanner_visual_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='FooterCTAConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('uuid', models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('eyebrow', models.CharField(blank=True, default='Empieza hoy', max_length=80)),
                ('title_prefix', models.CharField(blank=True, default='Impulsa tu empresa con', max_length=150)),
                ('title_highlighted', models.CharField(blank=True, default='Sintel Technology', max_length=100)),
                ('subtitle', models.CharField(
                    blank=True,
                    default='Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.',
                    max_length=300,
                )),
                ('btn_primary_label', models.CharField(blank=True, default='Solicitar cotizacion', max_length=80)),
                ('btn_primary_url', models.CharField(blank=True, default='/cotizar', max_length=200)),
                ('btn_ghost_label', models.CharField(blank=True, default='Explorar catalogo', max_length=80)),
                ('btn_ghost_url', models.CharField(blank=True, default='/tienda', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'config CTA final',
                'verbose_name_plural': 'config CTA final',
            },
        ),
    ]
