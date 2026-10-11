from django import forms
from django.utils.choices import CallableChoiceIterator

from apps.danh_muc.models import DichVu, KhuVuc, LoaiThietBi
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import DANG_XU_LY, TrangThaiDon
from apps.he_thong.bieu_mau import KieuBieuMau
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


def lua_chon_khung_gio(trong=True):
    ds = [(k, k) for k in cau_hinh("KHUNG_GIO")]
    return [("", "— chọn khung giờ —"), *ds] if trong else ds


class DichVuTheoNhomField(forms.ModelChoiceField):
    """Dịch vụ đang áp dụng, nhóm theo loại thiết bị (optgroup) để tổng đài chọn nhanh."""

    def __init__(self, **kwargs):
        super().__init__(queryset=DichVu.objects.filter(dang_ap_dung=True), **kwargs)

    def _lua_chon(self):
        nhom: dict[str, list] = {}
        for dv in self.queryset.order_by("loai_thiet_bi", "ten_dich_vu"):
            nhom.setdefault(dv.get_loai_thiet_bi_display(), []).append((dv.pk, dv.ten_dich_vu))
        return [("", "— chọn dịch vụ —"), *nhom.items()]

    def _get_choices(self):
        # Lười: chỉ truy vấn khi vẽ ô chọn. Truy vấn ngay sẽ chạy lúc import module (khai báo lớp form) →
        # mọi lệnh manage.py cần CSDL, kể cả lúc build image chưa có CSDL (A-94).
        return CallableChoiceIterator(self._lua_chon)

    choices = property(_get_choices, forms.ChoiceField.choices.fset)


class TiepNhanForm(KieuBieuMau, forms.Form):
    """UC02. Bắt buộc tối thiểu: SĐT, địa chỉ + khu vực, dịch vụ yêu cầu."""

    so_dien_thoai = forms.CharField(
        label="Số điện thoại khách",
        max_length=20,
        widget=forms.TextInput({"inputmode": "tel", "autofocus": True, "autocomplete": "off"}),
    )
    ho_ten = forms.CharField(label="Tên khách", max_length=100, required=False, help_text="Được để trống.")
    dia_chi_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    dia_chi_chi_tiet = forms.CharField(label="Địa chỉ mới", max_length=255, required=False)
    khu_vuc = forms.ModelChoiceField(
        label="Khu vực (địa chỉ mới)", queryset=KhuVuc.objects.all(), required=False
    )
    ghi_chu_duong_di = forms.CharField(
        label="Ghi chú đường đi", required=False, widget=forms.Textarea({"rows": 2})
    )
    thiet_bi_ids = forms.TypedMultipleChoiceField(
        coerce=int, required=False, widget=forms.MultipleHiddenInput
    )
    thiet_bi_moi_loai = forms.ChoiceField(
        label="Thiết bị mới — loại", choices=[("", "— không thêm —"), *LoaiThietBi.choices], required=False
    )
    thiet_bi_moi_hang = forms.CharField(label="Hãng", max_length=50, required=False)
    thiet_bi_moi_vi_tri = forms.CharField(label="Vị trí lắp", max_length=100, required=False)
    dich_vu_yeu_cau = DichVuTheoNhomField(label="Dịch vụ yêu cầu")
    mo_ta_su_co = forms.CharField(label="Mô tả sự cố", required=False, widget=forms.Textarea({"rows": 3}))
    kenh_tiep_nhan = forms.ChoiceField(
        label="Kênh tiếp nhận",
        choices=DonSuaChua.KenhTiepNhan.choices,
        initial=DonSuaChua.KenhTiepNhan.DIEN_THOAI,
    )
    ngay_hen = forms.DateField(label="Ngày hẹn", required=False, widget=forms.DateInput({"type": "date"}))
    khung_gio = forms.ChoiceField(label="Khung giờ", required=False)
    khung_gio_mong_muon = forms.CharField(
        label="Khung giờ mong muốn (khi chưa chốt)", max_length=100, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["khung_gio"].choices = lua_chon_khung_gio()
        # Ô chọn địa chỉ/thiết bị có sẵn do khối tra cứu (HTMX) vẽ; nhận mọi số nguyên, DAO kiểm tra thuộc khách.
        self.fields["thiet_bi_ids"].valid_value = lambda v: True

    def clean_so_dien_thoai(self):
        return chuan_hoa_sdt(self.cleaned_data["so_dien_thoai"])

    def clean(self):
        du_lieu = super().clean()
        if not du_lieu.get("dia_chi_id") and not (du_lieu.get("dia_chi_chi_tiet") or "").strip():
            self.add_error("dia_chi_chi_tiet", "Chọn địa chỉ có sẵn hoặc nhập địa chỉ mới.")
        elif not du_lieu.get("dia_chi_id") and not du_lieu.get("khu_vuc"):
            self.add_error("khu_vuc", "Địa chỉ mới bắt buộc chọn khu vực.")
        if bool(du_lieu.get("ngay_hen")) != bool(du_lieu.get("khung_gio")):
            self.add_error("khung_gio", "Chốt lịch cần cả ngày hẹn và khung giờ (hoặc để trống cả hai).")
        return du_lieu


class LichHenForm(KieuBieuMau, forms.Form):
    ngay = forms.DateField(label="Ngày hẹn", widget=forms.DateInput({"type": "date"}))
    khung_gio = forms.ChoiceField(label="Khung giờ")
    ly_do = forms.CharField(label="Lý do đổi hẹn", max_length=500, required=False)

    def __init__(self, *args, doi_hen=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["khung_gio"].choices = lua_chon_khung_gio(trong=False)
        if doi_hen:
            self.fields["ly_do"].required = True
        else:
            del self.fields["ly_do"]


class HuyDonForm(KieuBieuMau, forms.Form):
    ly_do = forms.CharField(label="Lý do hủy", widget=forms.Textarea({"rows": 3}))


class LocBangDonForm(forms.Form):
    ngay = forms.DateField(required=False, widget=forms.DateInput({"type": "date"}))
    khu_vuc = forms.ModelChoiceField(queryset=KhuVuc.objects.all(), required=False, empty_label="Mọi khu vực")
    trang_thai = forms.ChoiceField(required=False)
    tho = forms.IntegerField(required=False)
    q = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trang_thai"].choices = [("", "Mọi trạng thái")] + [
            (ma, nhan) for ma, nhan in TrangThaiDon.choices if ma in DANG_XU_LY
        ]
