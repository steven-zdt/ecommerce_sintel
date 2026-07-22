from django.db import migrations

TASK_NAME = "reconcile-pending-wompi-transactions"


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="*/5", hour="*", day_of_week="*", day_of_month="*", month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            "crontab": schedule,
            "task": "payment.tasks.reconcile_pending_wompi_transactions",
            "enabled": True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0007_alter_transaction_status_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_periodic_task, reverse_code=remove_periodic_task)]
