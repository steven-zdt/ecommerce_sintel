from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_homecardgroup'),
    ]

    operations = [
        # HomeModuleConfig - display_type and layout_config
        migrations.AddField(
            model_name='homemoduleconfig',
            name='display_type',
            field=models.CharField(
                choices=[
                    ('grid', 'Grid'), ('slider', 'Slider'), ('carousel', 'Carrusel'),
                    ('cards_h', 'Cards Horizontales'), ('cards_v', 'Cards Verticales'),
                    ('hero', 'Hero'), ('list', 'Lista'), ('highlight', 'Destacados'),
                ],
                default='grid', max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='homemoduleconfig',
            name='layout_config',
            field=models.JSONField(blank=True, default=dict),
        ),

        # HomeCard - card_type, animation, is_featured, priority
        migrations.AddField(
            model_name='homecard',
            name='card_type',
            field=models.CharField(
                choices=[
                    ('vertical', 'Vertical'), ('horizontal', 'Horizontal'),
                    ('premium', 'Premium'), ('compact', 'Compacta'),
                    ('glass', 'Glass'), ('dark', 'Dark'),
                    ('gradient', 'Gradient'), ('image_bg', 'Imagen de fondo'),
                ],
                default='vertical', max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='homecard',
            name='animation',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='homecard',
            name='is_featured',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='homecard',
            name='priority',
            field=models.PositiveIntegerField(default=0),
        ),

        # HomeCardGroup - visual builder fields
        migrations.AddField(
            model_name='homecardgroup',
            name='subtitle',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='bg_color',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='bg_image',
            field=models.ImageField(blank=True, null=True, upload_to='home_groups/'),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='layout_type',
            field=models.CharField(
                choices=[
                    ('grid', 'Grid'), ('slider', 'Slider'), ('cards', 'Cards'),
                    ('timeline', 'Timeline'), ('tabs', 'Tabs'), ('accordion', 'Accordion'),
                ],
                default='grid', max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='padding',
            field=models.CharField(
                choices=[
                    ('none', 'Sin padding'), ('sm', 'Pequeno'),
                    ('normal', 'Normal'), ('lg', 'Grande'), ('xl', 'Extra grande'),
                ],
                default='normal', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='divider',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='homecardgroup',
            name='columns',
            field=models.PositiveSmallIntegerField(default=3),
        ),
    ]
