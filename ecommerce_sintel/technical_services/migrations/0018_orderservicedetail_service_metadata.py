from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("technical_services", "0017_servicevariant_simultaneous_capacity_servicebooking"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderservicedetail",
            name="allow_schedule_changes",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="orderservicedetail",
            name="location_reference",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orderservicedetail",
            name="neighborhood",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="orderservicedetail",
            name="preferred_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderservicedetail",
            name="preferred_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderservicedetail",
            name="service_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
