import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0004_multipayment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenizedCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('token_id', models.CharField(max_length=255, unique=True)),
                ('masked_number', models.CharField(max_length=20)),
                ('brand', models.CharField(max_length=30)),
                ('exp_month', models.CharField(max_length=2)),
                ('exp_year', models.CharField(max_length=4)),
                ('cardholder_name', models.CharField(blank=True, default='', max_length=255)),
                ('is_default', models.BooleanField(db_index=True, default=False)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tokenized_cards',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'tarjeta tokenizada',
                'verbose_name_plural': 'tarjetas tokenizadas',
                'ordering': ['-created_at'],
            },
        ),
    ]
