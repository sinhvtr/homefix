from django import forms

from apps.he_thong.bieu_mau import KieuBieuMau
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt

from .models import DiaChi, DichVu, KhachHang, KhuVuc, ThietBi, Tho


class KhuVucForm(KieuBieuMau, forms.ModelForm):
    class Meta:
        model = KhuVuc
        fields = ["ma", "ten", "ghi_chu"]
        widgets = {"ghi_chu": forms.Textarea({"rows": 2})}


class DichVuForm(KieuBieuMau, forms.ModelForm):
    class Meta:
        model = DichVu
        fields = [
            "ma",
            "ten_dich_vu",
            "nhom_dich_vu",
            "loai_thiet_bi",
            "don_gia_tham_khao",
            "don_vi_tinh",
            "thoi_han_bao_hanh_ngay",
            "dang_ap_dung",
        ]
        help_texts = {
            "don_gia_tham_khao": "Đơn vị đồng. Với nhóm sửa chữa là giá “từ…”.",
            "thoi_han_bao_hanh_ngay": "Để trống = mặc định theo nhóm (7 ngày vệ sinh / 90 ngày sửa chữa).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["thoi_han_bao_hanh_ngay"].required = False
        self.fields["don_gia_tham_khao"].min_value = 0
        self.fields["don_gia_tham_khao"].widget.attrs["min"] = 0

    def clean_don_gia_tham_khao(self):
        gia = self.cleaned_data["don_gia_tham_khao"]
        if gia < 0:
            raise forms.ValidationError("Đơn giá không được âm.")
        return gia


def lua_chon_ky_nang():
    """Dịch vụ nhóm theo loại thiết bị để chọn kỹ năng thợ (UC13)."""
    nhom: dict[str, list] = {}
    for dv in DichVu.objects.order_by("loai_thiet_bi", "ten_dich_vu"):
        nhan = dv.ten_dich_vu if dv.dang_ap_dung else f"{dv.ten_dich_vu} (ngừng áp dụng)"
        nhom.setdefault(dv.get_loai_thiet_bi_display(), []).append((dv.pk, nhan))
    return list(nhom.items())


class ThoForm(KieuBieuMau, forms.ModelForm):
    so_dien_thoai = forms.CharField(
        label="Số điện thoại", max_length=20, widget=forms.TextInput({"inputmode": "tel"})
    )

    class Meta:
        model = Tho
        fields = [
            "ho_ten",
            "so_dien_thoai",
            "hinh_thuc",
            "ky_nang",
            "khu_vuc_phu_trach",
            "dang_nhan_viec",
            "nghi_den",
            "kenh_thong_bao",
            "ghi_chu",
        ]
        widgets = {
            "ky_nang": forms.CheckboxSelectMultiple,
            "khu_vuc_phu_trach": forms.CheckboxSelectMultiple,
            "nghi_den": forms.DateTimeInput({"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ghi_chu": forms.Textarea({"rows": 2}),
        }
        help_texts = {"nghi_den": "Để trống nếu không nghỉ."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ky_nang"].choices = lua_chon_ky_nang()

    def clean_so_dien_thoai(self):
        return chuan_hoa_sdt(self.cleaned_data["so_dien_thoai"])


class KhachHangForm(KieuBieuMau, forms.ModelForm):
    so_dien_thoai = forms.CharField(
        label="Số điện thoại", max_length=20, widget=forms.TextInput({"inputmode": "tel"})
    )
    so_dien_thoai_phu = forms.CharField(
        label="Số điện thoại phụ", max_length=20, required=False, widget=forms.TextInput({"inputmode": "tel"})
    )

    class Meta:
        model = KhachHang
        fields = ["ho_ten", "so_dien_thoai", "so_dien_thoai_phu", "vip_thu_cong", "ly_do_vip", "ghi_chu"]
        widgets = {"ghi_chu": forms.Textarea({"rows": 2})}
        help_texts = {"vip_thu_cong": "Giám đốc giới thiệu → VIP bất kể số lần sử dụng (BR07)."}

    def clean_so_dien_thoai(self):
        return chuan_hoa_sdt(self.cleaned_data["so_dien_thoai"])

    def clean_so_dien_thoai_phu(self):
        so = self.cleaned_data["so_dien_thoai_phu"]
        return chuan_hoa_sdt(so) if so else ""

    def clean(self):
        du_lieu = super().clean()
        if du_lieu.get("vip_thu_cong") and not (du_lieu.get("ly_do_vip") or "").strip():
            self.add_error("ly_do_vip", "Nhập lý do khi đánh dấu VIP thủ công.")
        return du_lieu


class DiaChiForm(KieuBieuMau, forms.ModelForm):
    class Meta:
        model = DiaChi
        fields = ["dia_chi_chi_tiet", "khu_vuc", "ghi_chu_duong_di", "la_mac_dinh"]
        widgets = {"ghi_chu_duong_di": forms.Textarea({"rows": 2})}

    def validate_unique(self):
        """Bỏ kiểm ràng buộc “một địa chỉ mặc định” ở form: DiaChiDAO bỏ mặc định cũ trước khi lưu."""


class ThietBiForm(KieuBieuMau, forms.ModelForm):
    class Meta:
        model = ThietBi
        fields = ["loai_thiet_bi", "hang_san_xuat", "model", "vi_tri_lap", "ghi_chu"]
        widgets = {"ghi_chu": forms.Textarea({"rows": 2})}


class TepExcelForm(KieuBieuMau, forms.Form):
    tep = forms.FileField(label="Tệp Excel (.xlsx)", widget=forms.ClearableFileInput({"accept": ".xlsx"}))

    def clean_tep(self):
        tep = self.cleaned_data["tep"]
        if not tep.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Chỉ nhận tệp .xlsx (tải tệp mẫu để điền).")
        if tep.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Tệp quá lớn (tối đa 2 MB).")
        return tep
