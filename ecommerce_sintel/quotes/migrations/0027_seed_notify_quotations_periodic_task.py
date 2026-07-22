from django.db import migrations

TASK_NAME = "notify-quotations-without-response"


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="9", day_of_week="*", day_of_month="*", month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            "crontab": schedule,
            "task": "quotes.tasks.notify_quotations_without_response",
            "enabled": True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0026_quotequestion_depends_on_question_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_periodic_task, reverse_code=remove_periodic_task)]
