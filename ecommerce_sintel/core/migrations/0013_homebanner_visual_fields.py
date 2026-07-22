from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_visual_builder'),
    ]

    operations = [
        migrations.AddField(
            model_name='homebanner',
            name='eyebrow',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='homebanner',
            name='background_color',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='homebanner',
            name='cta_ghost_label',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='homebanner',
            name='cta_ghost_url',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
