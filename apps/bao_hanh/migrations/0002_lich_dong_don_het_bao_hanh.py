"""Lịch tác vụ BR05 đóng đơn hết hạn bảo hành — hằng ngày 00:15 giờ Việt Nam (SPEC 12)."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import migrations

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def lan_chay_ke_tiep(gio: time) -> datetime:
    bay_gio = datetime.now(VN)
    moc = datetime.combine(bay_gio.date(), gio, tzinfo=VN)
    return moc if moc > bay_gio else moc + timedelta(days=1)


def tao_lich(apps, schema_editor):
    apps.get_model("django_q", "Schedule").objects.update_or_create(
        name="dong_don_het_bao_hanh",
        defaults={
            "func": "apps.bao_hanh.tac_vu.dong_don_het_bao_hanh",
            "schedule_type": "D",  # Schedule.DAILY
            "repeats": -1,
            "next_run": lan_chay_ke_tiep(time(0, 15)),
        },
    )


def xoa_lich(apps, schema_editor):
    apps.get_model("django_q", "Schedule").objects.filter(name="dong_don_het_bao_hanh").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bao_hanh", "0001_initial"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]

    operations = [migrations.RunPython(tao_lich, xoa_lich)]
