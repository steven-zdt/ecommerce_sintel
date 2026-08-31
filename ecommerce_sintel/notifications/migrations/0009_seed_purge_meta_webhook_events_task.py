from django.db import migrations

TASK_NAME = "purge-meta-webhook-events"


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Diaria a las 03:30 -- ventana de baja carga, igual criterio que el resto
    # de tareas de mantenimiento del proyecto.
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30", hour="3", day_of_week="*", day_of_month="*", month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            "crontab": schedule,
            "task": "notifications.purge_meta_webhook_events",
            "enabled": True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0008_metawebhookevent"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_periodic_task, reverse_code=remove_periodic_task)]
