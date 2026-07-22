import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_navbarlink_updated_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeCardGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("is_deleted", models.BooleanField(default=False, db_index=True)),
                ("name", models.CharField(db_index=True, max_length=100, unique=True)),
                ("title", models.CharField(max_length=150)),
                ("display_order", models.PositiveIntegerField(default=0, db_index=True)),
                ("is_visible", models.BooleanField(default=True, db_index=True)),
            ],
            options={
                "verbose_name": "grupo de tarjetas",
                "verbose_name_plural": "grupos de tarjetas",
                "ordering": ["display_order", "name"],
            },
        ),
    ]
