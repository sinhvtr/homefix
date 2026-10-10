"""DAO tài chính. P4: ghi nhận tiền thợ đã thu (UC09). P5: đối soát (UC12)."""

from apps.he_thong.nhat_ky import ghi_nhat_ky

from .models import ThanhToan


class ThanhToanDAO:
    @staticmethod
    def ghi_nhan(nguoi_dung, don, tho, so_tien: int, hinh_thuc: str, ly_do_lech: str = "", anh_chung_tu=None):
        """Gọi bên trong giao dịch hoàn thành đơn (T15). Ghi nhật ký GHI_TIEN (NFR06)."""
        tt = ThanhToan(
            don=don,
            tho=tho,
            so_tien=so_tien,
            hinh_thuc=hinh_thuc,
            trang_thai=ThanhToan.trang_thai_ban_dau(hinh_thuc, so_tien),
        )
        if anh_chung_tu is not None:
            tt.anh_chung_tu.save("chung_tu.jpg", anh_chung_tu, save=False)
        tt.save()
        ghi_nhat_ky(
            nguoi_dung,
            "GHI_TIEN",
            don,
            du_lieu_sau={
                "thanh_toan": tt.pk,
                "so_tien": so_tien,
                "hinh_thuc": hinh_thuc,
                "tong_tien_phai_thu": don.tong_tien_phai_thu,
                "ly_do_lech": ly_do_lech,
                "trang_thai": tt.trang_thai,
            },
        )
        return tt
