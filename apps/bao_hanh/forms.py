from django import forms

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.bieu_mau import KieuBieuMau
from apps.tiep_nhan_dieu_phoi.forms import lua_chon_khung_gio


class DonBaoHanhForm(KieuBieuMau, forms.Form):
    """UC11: lỗi khách báo lại + (tùy chọn) chốt lịch ngay → CHO_CU_THO; chưa chốt → chờ xác nhận lịch."""

    mo_ta_su_co = forms.CharField(label="Lỗi khách báo lại", widget=forms.Textarea({"rows": 3}))
    kenh_tiep_nhan = forms.ChoiceField(
        label="Kênh tiếp nhận",
        choices=DonSuaChua.KenhTiepNhan.choices,
        initial=DonSuaChua.KenhTiepNhan.DIEN_THOAI,
    )
    ngay_hen = forms.DateField(label="Ngày hẹn", required=False, widget=forms.DateInput({"type": "date"}))
    khung_gio = forms.ChoiceField(label="Khung giờ", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["khung_gio"].choices = lua_chon_khung_gio()
