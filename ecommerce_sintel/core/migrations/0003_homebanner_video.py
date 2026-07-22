from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_homebanner_core_homebanner_uuid_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='homebanner',
            name='video',
            field=models.FileField(blank=True, null=True, upload_to='home_banners/videos/'),
        ),
        migrations.AlterField(
            model_name='homebanner',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='home_banners/images/'),
        ),
    ]
