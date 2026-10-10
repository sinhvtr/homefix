"""DAO tiếp nhận (UC02) và lịch hẹn (UC03). Ghi: kiểm quyền, transaction.atomic(), khóa dòng đơn, ghi nhật ký."""

from dataclasses import dataclass, field
from datetime import date, datetime, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.danh_muc.dao import DiaChiDAO, KhachHangDAO, ThietBiDAO
from apps.danh_muc.models import DiaChi, KhachHang, ThietBi
from apps.don_sua_chua.dao import GHI_DON, DonSuaChuaDAO, ghi_doi_trang_thai
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt
from apps.tai_khoan.phan_quyen import kiem_tra_vai_tro

from .models import LichHen

T = TrangThaiDon
# Đổi hẹn khi đơn đã có lịch và thợ chưa bắt đầu làm (A-45)
DUOC_DOI_HEN = frozenset({T.CHO_CU_THO, T.DA_CO_THO})


def khoang_thoi_gian(ngay: date, khung_gio: str) -> tuple[datetime, datetime]:
    """('2026-10-12', '08:00-10:00') → hai thời điểm có múi giờ Asia/Ho_Chi_Minh."""
    try:
        bd, kt = (time.fromisoformat(p.strip()) for p in khung_gio.split("-"))
    except ValueError as loi:
        raise ValidationError({"khung_gio": f"Khung giờ “{khung_gio}” không hợp lệ."}) from loi
    bat_dau = timezone.make_aware(datetime.combine(ngay, bd))
    ket_thuc = timezone.make_aware(datetime.combine(ngay, kt))
    if ket_thuc <= bat_dau:
        raise ValidationError({"khung_gio": "Giờ kết thúc phải sau giờ bắt đầu."})
    return bat_dau, ket_thuc


class LichHenDAO:
    @staticmethod
    def _tao(nguoi_dung, don: DonSuaChua, bat_dau, ket_thuc, ly_do_doi_hen: str = "") -> LichHen:
        try:
            with transaction.atomic():
                return LichHen.objects.create(
                    don=don,
                    bat_dau=bat_dau,
                    ket_thuc=ket_thuc,
                    ly_do_doi_hen=ly_do_doi_hen,
                    nguoi_tao=nguoi_dung,
                )
        except IntegrityError as loi:  # ràng buộc "một lịch hiệu lực mỗi đơn" là lưới an toàn cuối
            raise ValidationError("Đơn đã có lịch hẹn hiệu lực — dùng “Đổi hẹn”.", code="trung_lich") from loi

    @staticmethod
    def lich_su(don: DonSuaChua):
        return don.ds_lich_hen.select_related("nguoi_tao").order_by("-tao_luc", "-id")

    @staticmethod
    def chot_lich(nguoi_dung, don: DonSuaChua, ngay: date, khung_gio: str) -> LichHen:
        """T3: khách chốt khung giờ cho đơn đang chờ xác nhận lịch."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        bat_dau, ket_thuc = khoang_thoi_gian(ngay, khung_gio)
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update().get(pk=don.pk)
            if don.trang_thai != T.CHO_XAC_NHAN_LICH:
                raise ValidationError(f"Đơn đang “{don.get_trang_thai_display()}”, không chốt lịch được.")
            lich = LichHenDAO._tao(nguoi_dung, don, bat_dau, ket_thuc)
            don.chot_lich(lich)
            ghi_nhat_ky(
                nguoi_dung, "CHOT_LICH", don, du_lieu_sau={"lich_hen": lich.pk, "khung_gio": lich.khung_gio}
            )
            ghi_doi_trang_thai(nguoi_dung, don)
        return lich

    @staticmethod
    def doi_hen(nguoi_dung, don: DonSuaChua, ngay: date, khung_gio: str, ly_do: str) -> LichHen:
        """Đổi hẹn: lịch cũ → DA_THAY_THE, tạo lịch mới HIEU_LUC [SRS]; trạng thái đơn giữ nguyên."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        if not (ly_do or "").strip():
            raise ValidationError({"ly_do": "Nhập lý do đổi hẹn."})
        bat_dau, ket_thuc = khoang_thoi_gian(ngay, khung_gio)
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update().get(pk=don.pk)
            if don.trang_thai not in DUOC_DOI_HEN:
                raise ValidationError(f"Đơn đang “{don.get_trang_thai_display()}”, không đổi hẹn được.")
            cu = don.ds_lich_hen.select_for_update().filter(trang_thai=LichHen.TrangThai.HIEU_LUC).first()
            if cu is None:
                raise ValidationError("Đơn chưa có lịch hiệu lực.")
            cu.trang_thai = LichHen.TrangThai.DA_THAY_THE
            cu.save(update_fields=["trang_thai", "cap_nhat_luc"])
            moi = LichHenDAO._tao(nguoi_dung, don, bat_dau, ket_thuc, ly_do.strip())
            ghi_nhat_ky(
                nguoi_dung,
                "DOI_HEN",
                don,
                {"lich_hen": cu.pk, "khung_gio": cu.khung_gio},
                {"lich_hen": moi.pk, "khung_gio": moi.khung_gio, "ly_do": ly_do.strip()},
            )
            # TODO-P3: đơn DA_CO_THO → thông báo thợ xác nhận lại (on_commit + tác vụ nền), UC03 [ĐX].
        return moi


@dataclass
class KetQuaTiepNhan:
    don: DonSuaChua
    khach_moi: bool
    ds_trung: list[str] = field(default_factory=list)


class TiepNhanDAO:
    @staticmethod
    def tiep_nhan(nguoi_dung, du_lieu: dict) -> KetQuaTiepNhan:
        """UC02: tạo/cập nhật khách, địa chỉ, thiết bị theo cuộc gọi rồi tạo đơn (T1 hoặc T2 + lịch hẹn) — một giao dịch.

        Tối thiểu: SĐT, địa chỉ + khu vực, dịch vụ yêu cầu. Được thiếu: tên khách, thiết bị, lịch.
        """
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        sdt = chuan_hoa_sdt(du_lieu["so_dien_thoai"])
        ho_ten = (du_lieu.get("ho_ten") or "").strip()
        dich_vu = du_lieu["dich_vu_yeu_cau"]
        if not dich_vu.dang_ap_dung:
            raise ValidationError({"dich_vu_yeu_cau": "Dịch vụ đã ngừng áp dụng."})
        ngay_hen, khung_gio = du_lieu.get("ngay_hen"), du_lieu.get("khung_gio")
        if bool(ngay_hen) != bool(khung_gio):
            raise ValidationError({"khung_gio": "Chốt lịch cần cả ngày hẹn và khung giờ."})
        da_chot_lich = bool(ngay_hen and khung_gio)
        khoang = khoang_thoi_gian(ngay_hen, khung_gio) if da_chot_lich else None

        with transaction.atomic():
            kh = (
                KhachHang.objects.select_for_update().filter(so_dien_thoai=sdt).first()
                or KhachHang.objects.select_for_update().filter(so_dien_thoai_phu=sdt).first()
            )
            khach_moi = kh is None
            if khach_moi:
                kh = KhachHangDAO.tao(nguoi_dung, {"so_dien_thoai": sdt, "ho_ten": ho_ten})
            elif ho_ten and not kh.ho_ten:
                kh = KhachHangDAO.sua(nguoi_dung, kh, {"ho_ten": ho_ten})

            dia_chi_id = du_lieu.get("dia_chi_id")
            if dia_chi_id:
                dc = DiaChi.objects.filter(pk=dia_chi_id, khach_hang=kh).first()
                if dc is None:
                    raise ValidationError({"dia_chi_id": "Địa chỉ không thuộc khách hàng này."})
            else:
                if not (du_lieu.get("dia_chi_chi_tiet") or "").strip() or not du_lieu.get("khu_vuc"):
                    raise ValidationError(
                        {"dia_chi_chi_tiet": "Chọn địa chỉ có sẵn hoặc nhập địa chỉ mới kèm khu vực."}
                    )
                dc = DiaChiDAO.tao(
                    nguoi_dung,
                    kh,
                    {
                        "dia_chi_chi_tiet": du_lieu["dia_chi_chi_tiet"].strip(),
                        "khu_vuc": du_lieu["khu_vuc"],
                        "ghi_chu_duong_di": du_lieu.get("ghi_chu_duong_di", ""),
                    },
                )

            ids = [int(i) for i in du_lieu.get("thiet_bi_ids") or []]
            thiet_bi = list(ThietBi.objects.filter(pk__in=ids, dia_chi=dc))
            if len(thiet_bi) != len(set(ids)):
                raise ValidationError({"thiet_bi_ids": "Thiết bị đã chọn không thuộc địa chỉ này."})
            if du_lieu.get("thiet_bi_moi_loai"):
                thiet_bi.append(
                    ThietBiDAO.tao(
                        nguoi_dung,
                        dc,
                        {
                            "loai_thiet_bi": du_lieu["thiet_bi_moi_loai"],
                            "hang_san_xuat": du_lieu.get("thiet_bi_moi_hang", ""),
                            "vi_tri_lap": du_lieu.get("thiet_bi_moi_vi_tri", ""),
                        },
                    )
                )

            don = DonSuaChuaDAO.tao_don(
                nguoi_dung,
                khach_hang=kh,
                dia_chi=dc,
                dich_vu=dich_vu,
                thiet_bi=thiet_bi,
                kenh_tiep_nhan=du_lieu["kenh_tiep_nhan"],
                mo_ta_su_co=du_lieu.get("mo_ta_su_co", ""),
                khung_gio_mong_muon=du_lieu.get("khung_gio_mong_muon", ""),
                da_chot_lich=da_chot_lich,
            )
            if da_chot_lich:  # T2: tạo LichHen trong cùng giao dịch
                lich = LichHenDAO._tao(nguoi_dung, don, *khoang)
                ghi_nhat_ky(
                    nguoi_dung,
                    "CHOT_LICH",
                    don,
                    du_lieu_sau={"lich_hen": lich.pk, "khung_gio": lich.khung_gio},
                )
            ds_trung = DonSuaChuaDAO.tim_don_trung(don)
        return KetQuaTiepNhan(don=don, khach_moi=khach_moi, ds_trung=ds_trung)
