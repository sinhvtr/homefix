"""Lịch tác vụ nền django-q2 (SPEC 12). P3: BR02 kiểm tra quá hạn phân công mỗi phút; dọn thông báo hằng tuần."""

from django.db import migrations

LICH = [
    {
        "name": "kiem_tra_qua_han_phan_cong",
        "func": "apps.tiep_nhan_dieu_phoi.tac_vu.kiem_tra_qua_han_phan_cong",
        "schedule_type": "I",  # Schedule.MINUTES
        "minutes": 1,
    },
    {
        "name": "don_dep_thong_bao",
        "func": "apps.thong_bao.tac_vu.don_dep_thong_bao",
        "schedule_type": "W",  # Schedule.WEEKLY
        "minutes": None,
    },
]


def tao_lich(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    for lich in LICH:
        Schedule.objects.update_or_create(
            name=lich["name"],
            defaults={
                "func": lich["func"],
                "schedule_type": lich["schedule_type"],
                "minutes": lich["minutes"],
                "repeats": -1,
            },
        )


def xoa_lich(apps, schema_editor):
    apps.get_model("django_q", "Schedule").objects.filter(name__in=[lich["name"] for lich in LICH]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tiep_nhan_dieu_phoi", "0002_phancong"),
        ("thong_bao", "0001_initial"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]

    operations = [migrations.RunPython(tao_lich, xoa_lich)]
