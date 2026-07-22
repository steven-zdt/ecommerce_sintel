"""
Elimina del modelo User los campos que migraron a accounts.UserProfile:
  first_name, last_name, phone_number, role.

Elimina los modelos UserProfile, VendorProfile y TechnicianProfile de la
app users (los datos ya fueron copiados en 0002 de accounts).

IMPORTANTE: Esta migración depende de accounts.0002 para garantizar que
los datos ya fueron transferidos antes de borrar las columnas.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_migrate_user_data_to_profiles"),
        ("technical_services", "0007_orderservicedetail_orderservicetimeline_and_more"),
        ("users", "0003_alter_user_role_technicianprofile"),
    ]

    operations = [
        # -- Eliminar M2M de TechnicianProfile antes de borrar el modelo ----
        migrations.RemoveField(model_name="technicianprofile", name="specialties"),
        migrations.RemoveField(model_name="technicianprofile", name="user"),
        migrations.DeleteModel(name="TechnicianProfile"),

        # -- Eliminar VendorProfile ------------------------------------------
        migrations.RemoveField(model_name="vendorprofile", name="user"),
        migrations.DeleteModel(name="VendorProfile"),

        # -- Eliminar UserProfile (users) ------------------------------------
        migrations.RemoveField(model_name="userprofile", name="user"),
        migrations.DeleteModel(name="UserProfile"),

        # -- Eliminar campos de autenticacion que van al perfil -------------
        migrations.RemoveField(model_name="user", name="first_name"),
        migrations.RemoveField(model_name="user", name="last_name"),
        migrations.RemoveField(model_name="user", name="phone_number"),
        migrations.RemoveField(model_name="user", name="role"),
    ]
