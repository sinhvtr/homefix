"""Màu trạng thái đơn dùng chung mọi nơi (SPEC 13) — định nghĩa một lần ở đây."""

from django import template
from django.utils.html import format_html

from apps.don_sua_chua.trang_thai import TrangThaiDon

register = template.Library()

T = TrangThaiDon
MAU = {
    T.CHO_XAC_NHAN_LICH: "bg-violet-100 text-violet-900 border-violet-300",
    T.CHO_CU_THO: "bg-orange-100 text-orange-900 border-orange-300",
    T.DA_CO_THO: "bg-sky-100 text-sky-900 border-sky-300",
    T.CHO_DUYET_GIA: "bg-yellow-100 text-yellow-900 border-yellow-300",
    T.DANG_SUA: "bg-blue-100 text-blue-900 border-blue-300",
    T.HOAN_THANH: "bg-green-100 text-green-900 border-green-300",
    T.DANG_BAO_HANH: "bg-teal-100 text-teal-900 border-teal-300",
    T.DA_HUY: "bg-slate-200 text-slate-700 border-slate-300",
    T.DA_DONG: "bg-slate-100 text-slate-500 border-slate-200",
}


@register.filter
def mau_trang_thai(trang_thai: str) -> str:
    return MAU.get(trang_thai, "bg-slate-100 text-slate-700 border-slate-300")


@register.simple_tag
def nhan_trang_thai(trang_thai: str):
    nhan = T(trang_thai).label if trang_thai in T.values else trang_thai
    return format_html(
        '<span class="inline-block rounded border px-2 py-0.5 text-sm font-medium {}">{}</span>',
        mau_trang_thai(trang_thai),
        nhan,
    )
