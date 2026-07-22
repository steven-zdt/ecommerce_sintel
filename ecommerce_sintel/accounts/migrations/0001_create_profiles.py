import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("technical_services", "0007_orderservicedetail_orderservicetimeline_and_more"),
        ("users", "0003_alter_user_role_technicianprofile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("first_name", models.CharField(blank=True, default="", max_length=50)),
                ("last_name", models.CharField(blank=True, default="", max_length=50)),
                ("phone_number", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("document", models.CharField(blank=True, max_length=30, null=True)),
                ("profile_picture", models.ImageField(blank=True, null=True, upload_to="profiles/pictures/")),
                ("company", models.CharField(blank=True, max_length=100, null=True)),
                ("position", models.CharField(blank=True, max_length=100, null=True)),
                ("address", models.CharField(blank=True, max_length=250, null=True)),
                ("city", models.CharField(blank=True, max_length=50, null=True)),
                ("state", models.CharField(blank=True, max_length=50, null=True)),
                ("country", models.CharField(blank=True, max_length=50, null=True)),
                ("postal_code", models.CharField(blank=True, max_length=10, null=True)),
                ("user_type", models.CharField(
                    choices=[
                        ("TECHNICIAN", "Tecnico"),
                        ("PROFESSIONAL", "Profesional"),
                        ("SPECIALIST", "Especialista"),
                    ],
                    default="TECHNICIAN",
                    max_length=20,
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "perfil de usuario",
                "verbose_name_plural": "perfiles de usuario",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="VendorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("store_name", models.CharField(max_length=100)),
                ("business_license", models.CharField(blank=True, max_length=100, null=True)),
                ("address", models.CharField(blank=True, max_length=250, null=True)),
                ("business_phone", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="vendor_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "perfil de proveedor",
                "verbose_name_plural": "perfiles de proveedores",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TechnicianProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("is_available", models.BooleanField(default=True)),
                ("specialties", models.ManyToManyField(
                    blank=True,
                    related_name="technician_profiles",
                    to="technical_services.servicecategory",
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="technician_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "perfil de tecnico",
                "verbose_name_plural": "perfiles de tecnicos",
                "abstract": False,
            },
        ),
    ]
