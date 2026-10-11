"""Chuyển tập con Markdown của docs/HUONG_DAN_SU_DUNG.md sang HTML cho trang /huong-dan/ (NFR09) — không thêm thư
viện ngoài Phụ lục B. Hỗ trợ: tiêu đề #/##/###, đoạn văn, danh sách `- ` và `1. ` (dòng thụt lề nối vào mục trước),
**đậm**, `mã`. Mọi văn bản được escape trước khi định dạng."""

import re
import unicodedata

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

_DAM = re.compile(r"\*\*(.+?)\*\*")
_MA = re.compile(r"`([^`]+)`")


def neo(chuoi: str) -> str:
    """'Tổng đài' → 'tong-dai' (đ không tách dấu được nên đổi tay)."""
    khong_dau = unicodedata.normalize("NFD", chuoi.replace("đ", "d").replace("Đ", "D"))
    khong_dau = "".join(c for c in khong_dau if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", khong_dau).strip("-")


def _dong(chuoi: str) -> str:
    chuoi = escape(chuoi)
    chuoi = _MA.sub(r'<code class="rounded bg-slate-100 px-1">\1</code>', chuoi)
    return _DAM.sub(r"<strong>\1</strong>", chuoi)


def sang_html(van_ban: str) -> tuple[SafeString, list[tuple[str, str]]]:
    """Trả (HTML, mục lục [(neo, tiêu đề cấp 2)])."""
    ra, muc_luc, doan, ds, the_ds = [], [], [], [], None

    def dong_doan():
        if doan:
            ra.append(f'<p class="mb-3">{_dong(" ".join(doan))}</p>')
            doan.clear()

    def dong_ds():
        nonlocal the_ds
        if ds:
            kieu = "list-decimal" if the_ds == "ol" else "list-disc"
            ra.append(
                f'<{the_ds} class="mb-3 {kieu} space-y-1 pl-6">'
                + "".join(f"<li>{_dong(m)}</li>" for m in ds)
                + f"</{the_ds}>"
            )
            ds.clear()
        the_ds = None

    for dong in van_ban.splitlines():
        if not dong.strip():
            dong_doan()
            dong_ds()
            continue
        tieu_de = re.match(r"^(#{1,3}) (.+)$", dong)
        muc = re.match(r"^(- |\d+\. )(.+)$", dong)
        if tieu_de:
            dong_doan()
            dong_ds()
            cap, chu = len(tieu_de.group(1)), tieu_de.group(2).strip()
            if cap == 1:
                continue  # tiêu đề trang do template đặt
            n = neo(chu)
            if cap == 2:
                muc_luc.append((n, chu))
            lop = "mt-8 mb-3 text-xl font-bold" if cap == 2 else "mt-5 mb-2 text-lg font-semibold"
            ra.append(f'<h{cap} id="{n}" class="{lop}">{_dong(chu)}</h{cap}>')
        elif muc:
            dong_doan()
            loai = "ol" if muc.group(1)[0].isdigit() else "ul"
            if the_ds and the_ds != loai:
                dong_ds()
            the_ds = loai
            ds.append(muc.group(2).strip())
        elif ds and dong.startswith("  "):
            ds[-1] += " " + dong.strip()
        else:
            dong_ds()
            doan.append(dong.strip())
    dong_doan()
    dong_ds()
    return mark_safe("\n".join(ra)), muc_luc  # noqa: S308 — mọi văn bản đã escape trong _dong
