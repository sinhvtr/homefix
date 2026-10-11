"""DAO bảo hành. P4: phát hành phiếu khi hoàn thành (BR05). P5: đơn bảo hành (UC11); tác vụ đóng đơn ở tac_vu.py."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.danh_muc.models import DichVu
from apps.don_sua_chua.dao import GHI_DON, KET_THUC_DON_BAO_HANH, DonSuaChuaDAO, ghi_doi_trang_thai
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.phan_quyen import kiem_tra_vai_tro
from apps.tiep_nhan_dieu_phoi.dao import LichHenDAO, khoang_thoi_gian

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

    # ------------------------------------------------------------ UC11 — đơn bảo hành / làm lại

    @staticmethod
    def kiem_tra_don_goc(don_goc: DonSuaChua) -> PhieuBaoHanh:
        """Đơn gốc phải HOAN_THANH (không đang có đơn bảo hành khác) và phiếu còn hạn; trả phiếu."""
        phieu = getattr(don_goc, "phieu_bao_hanh", None)
        if don_goc.loai_don != DonSuaChua.LoaiDon.THUONG or phieu is None:
            raise ValidationError("Đơn này không có phiếu bảo hành.", code="khong_co_phieu")
        if don_goc.trang_thai == TrangThaiDon.DANG_BAO_HANH:
            dang_lam = don_goc.ds_don_bao_hanh.exclude(trang_thai__in=KET_THUC_DON_BAO_HANH).first()
            raise ValidationError(
                f"Đơn gốc đang có đơn bảo hành {dang_lam.ma_don if dang_lam else ''} chưa xong.".replace(
                    "  ", " "
                ),
                code="dang_bao_hanh",
            )
        if not phieu.con_han:
            raise ValidationError(
                f"Phiếu {phieu.ma} đã hết hạn ngày {phieu.ngay_het_han:%d/%m/%Y} — tạo đơn thường.",
                code="het_han",
            )
        if don_goc.trang_thai != TrangThaiDon.HOAN_THANH:
            raise ValidationError(
                f"Đơn gốc đang “{don_goc.get_trang_thai_display()}”, không tạo đơn bảo hành được.",
                code="sai_trang_thai",
            )
        return phieu

    @staticmethod
    def tao_don_bao_hanh(
        nguoi_dung,
        don_goc: DonSuaChua,
        *,
        mo_ta_su_co: str,
        kenh_tiep_nhan: str = DonSuaChua.KenhTiepNhan.DIEN_THOAI,
        ngay_hen: date | None = None,
        khung_gio: str = "",
    ) -> DonSuaChua:
        """UC11: tạo DonSuaChua(BAO_HANH) cùng khách, địa chỉ, thiết bị, dịch vụ của đơn gốc; nguyên nhân
        CHUA_XAC_DINH; có lịch thì vào thẳng CHO_CU_THO (T2); đơn gốc → DANG_BAO_HANH (T16). Một giao dịch."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        if not (mo_ta_su_co or "").strip():
            raise ValidationError({"mo_ta_su_co": "Mô tả lỗi khách báo lại."})
        if bool(ngay_hen) != bool(khung_gio):
            raise ValidationError({"khung_gio": "Chốt lịch cần cả ngày hẹn và khung giờ."})
        khoang = khoang_thoi_gian(ngay_hen, khung_gio) if ngay_hen else None
        with transaction.atomic():
            goc = (
                DonSuaChua.objects.select_for_update(of=("self",))
                .select_related("phieu_bao_hanh", "khach_hang", "dia_chi", "dich_vu_yeu_cau")
                .get(pk=don_goc.pk)
            )
            phieu = BaoHanhDAO.kiem_tra_don_goc(goc)
            don_bh = DonSuaChuaDAO.tao_don(
                nguoi_dung,
                khach_hang=goc.khach_hang,
                dia_chi=goc.dia_chi,
                dich_vu=goc.dich_vu_yeu_cau,
                thiet_bi=list(goc.thiet_bi.all()),
                kenh_tiep_nhan=kenh_tiep_nhan,
                mo_ta_su_co=mo_ta_su_co.strip(),
                da_chot_lich=khoang is not None,
                loai_don=DonSuaChua.LoaiDon.BAO_HANH,
                don_goc=goc,
            )
            if khoang is not None:
                lich = LichHenDAO._tao(nguoi_dung, don_bh, *khoang)
                ghi_nhat_ky(
                    nguoi_dung,
                    "CHOT_LICH",
                    don_bh,
                    du_lieu_sau={"lich_hen": lich.pk, "khung_gio": lich.khung_gio},
                )
            goc.mo_bao_hanh(don_bh)
            ghi_nhat_ky(
                nguoi_dung,
                "TAO_DON_BAO_HANH",
                goc,
                du_lieu_sau={
                    "don_bao_hanh": don_bh.ma_don,
                    "phieu": phieu.ma,
                    "ngay_het_han": phieu.ngay_het_han,
                },
            )
            ghi_doi_trang_thai(nguoi_dung, goc)
        return don_bh
