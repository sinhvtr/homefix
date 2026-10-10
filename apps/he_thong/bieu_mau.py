"""Tiện ích form dùng chung: gắn lớp CSS cho widget, đổ lỗi ValidationError của DAO vào form."""

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

LOP_O_NHAP = "block w-full min-h-11 rounded border border-slate-300 px-3 py-2"
LOP_HOP_KIEM = "h-5 w-5"


class KieuBieuMau:
    """Mixin: thêm lớp Tailwind cho mọi widget (vùng bấm ≥ 44px — NFR08)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for truong in self.fields.values():
            w = truong.widget
            if isinstance(w, forms.CheckboxInput):
                lop = LOP_HOP_KIEM
            elif isinstance(w, forms.CheckboxSelectMultiple):
                continue
            else:
                lop = LOP_O_NHAP
            w.attrs["class"] = f"{w.attrs.get('class', '')} {lop}".strip()


def gan_loi_vao_form(form, loi: ValidationError) -> None:
    """Lỗi từ DAO: lỗi theo trường gắn dưới ô (nếu form có trường đó), còn lại là lỗi chung."""
    if hasattr(loi, "error_dict"):
        for truong, ds in loi.error_dict.items():
            form.add_error(truong if truong in form.fields else None, ds)
    else:
        form.add_error(None, loi)


__all__ = ["KieuBieuMau", "gan_loi_vao_form", "NON_FIELD_ERRORS"]
