"""DAO bảo hành. P4: phát hành phiếu khi hoàn thành (BR05). P5: đơn bảo hành, đóng đơn hết hạn (UC11)."""

from datetime import date, timedelta

from apps.danh_muc.models import DichVu
from apps.he_thong.nhat_ky import ghi_nhat_ky

from .models import PhieuBaoHanh

MAU_DIEU_KIEN = {
    DichVu.NhomDichVu.VE_SINH_BAO_DUONG: (
        "Bảo hành {so_ngay} ngày cho hạng mục vệ sinh, bảo dưỡng đã thực hiện (đến hết ngày {het_han}). "
        "Không áp dụng khi thiết bị bị tác động, sửa chữa bởi bên khác hoặc hỏng do nguồn điện, nước."
    ),
    DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU: (
        "Bảo hành {so_ngay} ngày cho hạng mục sửa chữa và vật tư đã thay (đến hết ngày {het_han}). "
        "Lỗi do tay nghề: thợ làm lại miễn phí; lỗi vật tư: công ty chịu chi phí thay thế. "
        "Không áp dụng khi tem bảo hành bị rách hoặc thiết bị bị tác động bởi bên khác."
    ),
}


class BaoHanhDAO:
    @staticmethod
    def so_ngay_bao_hanh(don) -> int:
        """BR05: max(thời hạn bảo hành) của các dịch vụ trong đơn (dịch vụ yêu cầu + dịch vụ của dòng tiền công)."""
        ds = [don.dich_vu_yeu_cau.thoi_han_bao_hanh_ngay]
        ds += [
            hm.dich_vu.thoi_han_bao_hanh_ngay
            for hm in don.ds_hang_muc.select_related("dich_vu")
            if hm.dich_vu
        ]
        return max(ds)

    @staticmethod
    def phat_hanh(nguoi_dung, don, ngay_hoan_thanh: date) -> PhieuBaoHanh:
        """Gọi bên trong giao dịch hoàn thành (T15): ngay_het_han = ngày hoàn thành + số ngày bảo hành."""
        so_ngay = BaoHanhDAO.so_ngay_bao_hanh(don)
        het_han = ngay_hoan_thanh + timedelta(days=so_ngay)
        nhom = (
            DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU
            if any(
                hm.dich_vu and hm.dich_vu.nhom_dich_vu == DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU
                for hm in don.ds_hang_muc.select_related("dich_vu")
            )
            else don.dich_vu_yeu_cau.nhom_dich_vu
        )
        phieu = PhieuBaoHanh.objects.create(
            ma=f"BH-{don.ma_don}",
            don=don,
            ngay_bat_dau=ngay_hoan_thanh,
            ngay_het_han=het_han,
            dieu_kien=MAU_DIEU_KIEN[nhom].format(so_ngay=so_ngay, het_han=f"{het_han:%d/%m/%Y}"),
        )
        ghi_nhat_ky(
            nguoi_dung,
            "PHAT_HANH_BAO_HANH",
            don,
            du_lieu_sau={"phieu": phieu.ma, "ngay_het_han": het_han, "so_ngay": so_ngay},
        )
        return phieu
