"""Lịch tác vụ nền django-q2 (SPEC 12: lịch đặt trong migration dữ liệu). P2: BR08 nhắc xác nhận lịch mỗi giờ."""

from django.db import migrations

LICH = [
    {
        "name": "nhac_xac_nhan_lich",
        "func": "apps.don_sua_chua.tac_vu.nhac_xac_nhan_lich",
        "schedule_type": "H",  # Schedule.HOURLY
    },
]


def tao_lich(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    for lich in LICH:
        Schedule.objects.update_or_create(
            name=lich["name"], defaults={"func": lich["func"], "schedule_type": lich["schedule_type"], "repeats": -1}
        )


def xoa_lich(apps, schema_editor):
    apps.get_model("django_q", "Schedule").objects.filter(name__in=[lich["name"] for lich in LICH]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("don_sua_chua", "0001_initial"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]

    operations = [migrations.RunPython(tao_lich, xoa_lich)]
