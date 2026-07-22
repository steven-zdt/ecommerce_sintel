from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_footer_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homemoduleconfig',
            name='module_key',
            field=models.CharField(max_length=40, unique=True),
        ),
        migrations.AddField(
            model_name='homemoduleconfig',
            name='custom_label',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='homemoduleconfig',
            name='custom_icon',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='homemoduleconfig',
            name='custom_url',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='homemoduleconfig',
            name='custom_color',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
