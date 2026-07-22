from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_alter_userauditlog_action'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='emailverificationcode',
            index=models.Index(
                fields=['email', 'is_used'],
                name='email_verif_email_used_idx',
            ),
        ),
    ]
