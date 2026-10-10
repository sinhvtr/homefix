"""Nội dung thông báo cho các sự kiện điều phối (SPEC 11). Gửi qua DichVuThongBao: bản ghi trong ứng dụng ngay,
kênh ngoài sau khi commit."""

from django.utils import timezone

from apps.thong_bao.dich_vu import DichVuThongBao

from .models import PhanCong


def _tom_tat(don) -> str:
    lich = don.lich_hieu_luc
    gio = lich.khung_gio if lich else (don.khung_gio_mong_muon or "chưa có giờ")
    return f"{don.dich_vu_yeu_cau.ten_dich_vu} · {don.dia_chi.khu_vuc} · {gio}"


def gui_de_nghi_nhan_viec(pc: PhanCong) -> None:
    """Gửi đề nghị cho thợ (UC04 bước 4). Không lộ SĐT, địa chỉ chi tiết (NFR04)."""
    han = timezone.localtime(pc.han_phan_hoi)
    DichVuThongBao.gui(
        pc.tho.nguoi_dung,
        f"Việc mới {pc.don.ma_don}",
        f"{_tom_tat(pc.don)} · công dự kiến {pc.tien_cong_du_kien:,} đ · trả lời trước {han:%H:%M}".replace(
            ",", "."
        ),
        f"/tho/de-nghi/{pc.pk}/",
    )


def bao_tho(pc: PhanCong, tieu_de: str, noi_dung: str = "", duong_dan: str = "/tho/") -> None:
    DichVuThongBao.gui(pc.tho.nguoi_dung, tieu_de, noi_dung, duong_dan)


def bao_tong_dai(nguoi_nhan, don, tieu_de: str, noi_dung: str = "") -> None:
    if nguoi_nhan is None:
        return
    DichVuThongBao.gui(nguoi_nhan, tieu_de, noi_dung or _tom_tat(don), f"/don/{don.ma_don}/cu-tho/")
