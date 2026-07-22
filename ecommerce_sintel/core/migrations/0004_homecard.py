from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_homebanner_video'),
    ]

    operations = [
        migrations.CreateModel(
            name='HomeCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('title', models.CharField(max_length=120)),
                ('subtitle', models.CharField(blank=True, default='', max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('group_name', models.CharField(db_index=True, max_length=100)),
                ('icon_class', models.CharField(default='bi-star', max_length=80)),
                ('background_color', models.CharField(default='#3b82f6', max_length=30)),
                ('redirect_url', models.CharField(blank=True, default='', max_length=500)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'tarjeta de inicio',
                'verbose_name_plural': 'tarjetas de inicio',
                'ordering': ['group_name', 'display_order'],
            },
        ),
    ]
