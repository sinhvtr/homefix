"""Hoàn thành đơn (UC09 — Phụ lục C: DonSuaChuaDAO.hoan_thanh). Đặt ở app thực hiện vì cần tạo ThanhToan
(tai_chinh) và PhieuBaoHanh (bao_hanh) — gói lõi ở tầng dưới không được import hai lớp này (A-69)."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.bao_hanh.dao import BaoHanhDAO
from apps.bao_hanh.models import PhieuBaoHanh
from apps.don_sua_chua.dao import DonSuaChuaDAO as LoiDonSuaChuaDAO
from apps.don_sua_chua.dao import HienTruongDAO, ghi_doi_trang_thai, nguoi_dieu_phoi
from apps.don_sua_chua.models import AnhHienTruong, DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.anh import nen_anh
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_chinh.dao import ThanhToanDAO
from apps.tai_chinh.models import ThanhToan
from apps.thong_bao.dich_vu import DichVuThongBao


@dataclass
class KetQuaHoanThanh:
    don: DonSuaChua
    thanh_toan: ThanhToan
    phieu_bao_hanh: PhieuBaoHanh | None


class DonSuaChuaDAO(LoiDonSuaChuaDAO):
    @staticmethod
    def hoan_thanh(
        nguoi_dung,
        don: DonSuaChua,
        so_tien: int,
        hinh_thuc: str,
        ly_do_lech: str = "",
        anh_chung_tu=None,
    ) -> KetQuaHoanThanh:
        """T15: điều kiện đã nhập tiền thu và đủ ảnh. Chốt tong_tien_phai_thu (mục 7.2), tạo ThanhToan, phát hành
        PhieuBaoHanh (đơn thường), báo tổng đài — tất cả trong MỘT giao dịch; thông báo gửi sau commit."""
        HienTruongDAO.kiem_tra_tho_cua_don(nguoi_dung, don)
        if hinh_thuc not in ThanhToan.HinhThuc.values:
            raise ValidationError({"hinh_thuc": "Chọn hình thức thu tiền."})
        if so_tien is None or int(so_tien) < 0:
            raise ValidationError({"so_tien": "Nhập số tiền đã thu (≥ 0 đ)."})
        noi_dung_chung_tu = nen_anh(anh_chung_tu)[0] if anh_chung_tu else None
        with transaction.atomic():
            don = (
                DonSuaChua.objects.select_for_update(of=("self",))
                .select_related("tho", "khach_hang")
                .get(pk=don.pk)
            )
            if don.trang_thai != TrangThaiDon.DANG_SUA:
                raise ValidationError(f"Đơn đang “{don.get_trang_thai_display()}”, chưa hoàn thành được.")
            tong = don.tong_tien
            if int(so_tien) != tong and not (ly_do_lech or "").strip():
                raise ValidationError(
                    {"ly_do_lech": f"Số thu khác tổng phải thu ({tong:,} đ) — ghi lý do.".replace(",", ".")}
                )
            so_anh = don.ds_anh.filter(loai=AnhHienTruong.Loai.HIEN_TRUONG).count()
            don.hoan_thanh(int(so_tien), so_anh)  # ném lỗi nếu thiếu ảnh (điều kiện T15)
            tt = ThanhToanDAO.ghi_nhan(
                nguoi_dung,
                don,
                don.tho,
                int(so_tien),
                hinh_thuc,
                (ly_do_lech or "").strip(),
                noi_dung_chung_tu,
            )
            phieu = None
            if don.loai_don == DonSuaChua.LoaiDon.THUONG:  # đơn bảo hành không gia hạn bảo hành (A-25)
                phieu = BaoHanhDAO.phat_hanh(nguoi_dung, don, timezone.localdate())
            ghi_nhat_ky(
                nguoi_dung,
                "HOAN_THANH",
                don,
                du_lieu_sau={"tong_tien_phai_thu": don.tong_tien_phai_thu, "so_anh": so_anh},
            )
            ghi_doi_trang_thai(nguoi_dung, don)
            nguoi_nhan = nguoi_dieu_phoi(don)
        DichVuThongBao.gui(
            nguoi_nhan,
            f"{don.tho.ho_ten} đã hoàn thành {don.ma_don}",
            f"Thu {int(so_tien):,} đ · {tt.get_hinh_thuc_display()}".replace(",", "."),
            f"/don/{don.ma_don}/",
        )
        return KetQuaHoanThanh(don=don, thanh_toan=tt, phieu_bao_hanh=phieu)
