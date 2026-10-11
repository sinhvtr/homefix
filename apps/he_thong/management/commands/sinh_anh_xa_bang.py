"""Sinh docs/ANH_XA_BANG.md từ `_meta` mọi model của dự án: lớp ↔ bảng ↔ cột ↔ kiểu (SPEC 15-P6).

Kết quả tất định (không có thời điểm sinh) để kiểm thử so sánh được: `--kiem-tra` báo lỗi nếu tệp đang có khác
nội dung sinh mới (quên chạy lại lệnh sau khi đổi mô hình).
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, models

TEP_MAC_DINH = Path(settings.BASE_DIR) / "docs" / "ANH_XA_BANG.md"


def _o(chuoi) -> str:
    return str(chuoi).replace("|", "\\|").replace("\n", " ")


def _rang_buoc(f) -> str:
    phan = []
    if f.primary_key:
        phan.append("PK")
    if f.unique and not f.primary_key:
        phan.append("UNIQUE")
    if f.many_to_one or f.one_to_one:
        dich = f.related_model
        phan.append(f"FK → {dich._meta.db_table} ({dich.__name__}), {f.remote_field.on_delete.__name__}")
    if f.choices:
        phan.append("chọn: " + ", ".join(str(ma) for ma, _ in f.flatchoices))
    if f.has_default() and not f.primary_key and not callable(f.default):
        phan.append(f"mặc định {getattr(f.default, 'value', f.default)!r}")
    return "; ".join(phan)


def _mo_hinh_du_an():
    for app in apps.get_app_configs():
        if app.name.startswith("apps."):
            yield from sorted(app.get_models(), key=lambda m: m._meta.db_table)


def sinh_noi_dung() -> str:
    dong = [
        "# Ánh xạ lớp ↔ bảng ↔ cột ↔ kiểu",
        "",
        "Sinh tự động bằng `python manage.py sinh_anh_xa_bang` từ `_meta` của các model — **không sửa tay**.",
        "Kiểu CSDL theo PostgreSQL 16. Mọi bảng kế thừa `MoHinhCoBan` có thêm `tao_luc`, `cap_nhat_luc`.",
        "",
        "## Mục lục",
        "",
    ]
    ds = list(_mo_hinh_du_an())
    dong += [f"- `{m.__name__}` → `{m._meta.db_table}` ({m._meta.app_label})" for m in ds]
    for m in ds:
        meta = m._meta
        dong += ["", f"## {m.__name__} → `{meta.db_table}`", ""]
        dong.append(f"App `{meta.app_label}` · {_o(meta.verbose_name)}")
        if m.__doc__ and not m.__doc__.startswith(f"{m.__name__}("):
            dong.append(f"\n> {_o(m.__doc__.strip().splitlines()[0])}")
        dong += [
            "",
            "| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |",
            "|---|---|---|---|---|---|---|",
        ]
        for f in meta.get_fields(include_hidden=False):
            if not f.concrete or f.many_to_many or f.auto_created and not f.primary_key:
                continue
            dong.append(
                f"| `{f.name}` | `{f.column}` | {f.get_internal_type()} | {_o(f.db_type(connection) or '')} "
                f"| {'có' if f.null else ''} | {_o(_rang_buoc(f))} | {_o(f.verbose_name)} |"
            )
        nhieu_nhieu = [f for f in meta.local_many_to_many]
        if nhieu_nhieu:
            dong += ["", "Quan hệ nhiều–nhiều (bảng trung gian):", ""]
            for f in nhieu_nhieu:
                dich = f.related_model
                dong.append(
                    f"- `{f.name}` → `{dich._meta.db_table}` ({dich.__name__}) qua bảng "
                    f"`{f.remote_field.through._meta.db_table}`"
                )
        rang_buoc = [c for c in meta.constraints]
        if rang_buoc:
            dong += ["", "Ràng buộc CSDL:", ""]
            for c in rang_buoc:
                if isinstance(c, models.UniqueConstraint):
                    mo_ta = f"UNIQUE ({', '.join(c.fields)})" + (
                        f" WHERE {c.condition}" if c.condition else ""
                    )
                else:
                    mo_ta = f"CHECK {getattr(c, 'condition', '')}"
                dong.append(f"- `{c.name}`: {_o(mo_ta)}")
        if meta.indexes:
            dong += ["", "Chỉ mục:", ""]
            dong += [f"- `{i.name}`: ({', '.join(i.fields)})" for i in meta.indexes]
    return "\n".join(dong) + "\n"


class Command(BaseCommand):
    help = "Sinh docs/ANH_XA_BANG.md (lớp ↔ bảng ↔ cột ↔ kiểu) từ _meta mọi model."

    def add_arguments(self, parser):
        parser.add_argument("--tep", default=str(TEP_MAC_DINH), help="Đường dẫn tệp kết quả.")
        parser.add_argument("--kiem-tra", action="store_true", help="Chỉ so sánh; khác thì báo lỗi.")

    def handle(self, *args, tep, kiem_tra=False, **options):
        duong_dan = Path(tep)
        noi_dung = sinh_noi_dung()
        if kiem_tra:
            hien_co = duong_dan.read_text(encoding="utf-8") if duong_dan.exists() else ""
            if hien_co != noi_dung:
                raise CommandError(f"{duong_dan} đã cũ — chạy `python manage.py sinh_anh_xa_bang`.")
            self.stdout.write(self.style.SUCCESS(f"{duong_dan} khớp mô hình hiện tại."))
            return
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        duong_dan.write_text(noi_dung, encoding="utf-8", newline="\n")
        self.stdout.write(self.style.SUCCESS(f"Đã ghi {duong_dan} ({noi_dung.count('## ') - 1} lớp)."))
