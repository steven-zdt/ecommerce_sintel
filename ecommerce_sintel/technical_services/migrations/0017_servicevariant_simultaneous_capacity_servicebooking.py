import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("technical_services", "0016_variant_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicevariant",
            name="simultaneous_capacity",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Numero maximo de servicios de este tipo que se pueden ejecutar al mismo tiempo.",
            ),
        ),
        migrations.CreateModel(
            name="ServiceBooking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Programado"),
                            ("active",    "En progreso"),
                            ("completed", "Completado"),
                            ("cancelled", "Cancelado"),
                        ],
                        default="scheduled",
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("start_time", models.DateTimeField(db_index=True)),
                ("end_time",   models.DateTimeField(db_index=True)),
                (
                    "order_service_detail",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="technical_services.orderservicedetail",
                    ),
                ),
                (
                    "service_variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="technical_services.servicevariant",
                    ),
                ),
            ],
            options={
                "verbose_name": "reserva de servicio",
                "verbose_name_plural": "reservas de servicio",
            },
        ),
        migrations.AddIndex(
            model_name="servicebooking",
            index=models.Index(
                fields=["start_time", "end_time"],
                name="tech_svc_booking_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="servicebooking",
            index=models.Index(
                fields=["service_variant", "status"],
                name="tech_svc_booking_var_status_idx",
            ),
        ),
    ]
