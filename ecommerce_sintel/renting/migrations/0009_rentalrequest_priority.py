from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('renting', '0008_multipayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalrequest',
            name='priority',
            field=models.CharField(
                choices=[('LOW', 'Baja'), ('HIGH', 'Alta')],
                default='LOW',
                db_index=True,
                max_length=10,
            ),
        ),
    ]
