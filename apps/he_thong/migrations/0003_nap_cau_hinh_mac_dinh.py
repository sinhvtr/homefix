"""Nạp tham số nghiệp vụ mặc định (SPEC 8.2). Không ghi đè giá trị quản trị đã sửa."""

from django.db import migrations

from apps.he_thong.cau_hinh import MAC_DINH


def nap(apps, schema_editor):
    CauHinh = apps.get_model("he_thong", "CauHinh")
    for khoa, (gia_tri, kieu, mo_ta) in MAC_DINH.items():
        CauHinh.objects.get_or_create(khoa=khoa, defaults={"gia_tri": gia_tri, "kieu": kieu, "mo_ta": mo_ta})


class Migration(migrations.Migration):
    dependencies = [("he_thong", "0002_initial")]

    operations = [migrations.RunPython(nap, migrations.RunPython.noop)]
