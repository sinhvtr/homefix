"""DAO tài chính. P4: ghi nhận tiền thợ đã thu (UC09). P5: đối soát tiền thợ đã thu (UC12).

Một dòng phiếu đối soát = một ThanhToan (khóa ngoại `phieu_doi_soat` → không thể nằm ở hai phiếu). Vật tư thợ ứng
của đơn đi kèm ThanhToan của đơn đó (A-78), nên bỏ chọn một dòng là bỏ cả tiền thu lẫn vật tư ứng của đơn.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.danh_muc.models import Tho
from apps.don_sua_chua.models import HangMucSuaChua
from apps.don_sua_chua.tinh_tien import thanh_tien
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.phan_quyen import GD, KT, QT, THO, co_vai_tro, kiem_tra_vai_tro
from apps.thong_bao.dich_vu import DichVuThongBao

from .models import PhieuDoiSoat, ThanhToan

GHI_DOI_SOAT = (KT,)  # SPEC 3.1: Phiếu đối soát — KT CRU
XEM_DOI_SOAT = (KT, QT, GD)  # QT, GĐ: R; thợ: R phiếu của mình
PT = PhieuDoiSoat.TrangThai
TT = ThanhToan.TrangThai


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


# ====================================================================== UC12 — đối soát


def tien_vat_tu_ung(hm: HangMucSuaChua) -> int:
    """Số công ty hoàn cho thợ: số lượng × giá mua; không ghi giá mua thì theo giá bán (A-78)."""
    return thanh_tien(hm.so_luong, hm.gia_mua if hm.gia_mua is not None else hm.don_gia_thuc_te)


def tien_thu_phai_nop(tt: ThanhToan) -> int:
    """Tiền mặt / CK cho thợ (CHUA_NOP hoặc đã nộp qua phiếu); CK công ty và 0 đ không tính."""
    return tt.so_tien if tt.trang_thai in (TT.CHUA_NOP, TT.DA_NOP) else 0


def _vat_tu_ung_theo_don(ds_don_id) -> dict[int, list[HangMucSuaChua]]:
    kq: dict[int, list[HangMucSuaChua]] = {}
    for hm in HangMucSuaChua.objects.filter(
        don_id__in=set(ds_don_id), loai=HangMucSuaChua.Loai.VAT_TU, nguoi_ung=HangMucSuaChua.NguoiUng.THO
    ).order_by("don_id", "id"):
        kq.setdefault(hm.don_id, []).append(hm)
    return kq


@dataclass
class DongDoiSoat:
    thanh_toan: ThanhToan
    ds_vat_tu: list[HangMucSuaChua]
    tien_thu: int
    tien_vat_tu: int


@dataclass
class TongHopTho:
    """Một dòng bảng tổng hợp /ke-toan/doi-soat/ (UC12)."""

    tho: Tho
    ma_tho: str
    tien_chua_nop: int = 0
    vat_tu_chua_hoan: int = 0
    so_phai_nop: int = 0
    so_ngay_cu_nhat: int | None = None
    so_dong_cho_doi_soat: int = 0
    phieu_nhap: list = field(default_factory=list)


def _dong(ds_tt, vat_tu: dict | None = None) -> list[DongDoiSoat]:
    ds_tt = list(ds_tt)
    vat_tu = vat_tu if vat_tu is not None else _vat_tu_ung_theo_don(tt.don_id for tt in ds_tt)
    return [
        DongDoiSoat(
            thanh_toan=tt,
            ds_vat_tu=vat_tu.get(tt.don_id, []),
            tien_thu=tien_thu_phai_nop(tt),
            tien_vat_tu=sum(tien_vat_tu_ung(hm) for hm in vat_tu.get(tt.don_id, [])),
        )
        for tt in ds_tt
    ]


def _cho_doi_soat(tho_id) -> Q:
    """ThanhToan chưa vào phiếu nào mà còn việc cần đối soát: tiền chưa nộp hoặc đơn có vật tư thợ ứng."""
    return Q(tho_id=tho_id, phieu_doi_soat__isnull=True) & (
        Q(trang_thai=TT.CHUA_NOP)
        | Q(
            don__ds_hang_muc__loai=HangMucSuaChua.Loai.VAT_TU,
            don__ds_hang_muc__nguoi_ung=HangMucSuaChua.NguoiUng.THO,
        )
    )


class DoiSoatDAO:
    # ------------------------------------------------------------ đọc

    @staticmethod
    def tong_hop_theo_tho(nguoi_dung) -> list[TongHopTho]:
        """Theo thợ: tiền mặt + CK cho thợ chưa nộp, vật tư thợ ứng chưa hoàn (đơn chưa nằm trong phiếu DA_NOP),
        số phải nộp, đơn cũ nhất chưa nộp (số ngày). Sắp theo số phải nộp giảm dần."""
        kiem_tra_vai_tro(nguoi_dung, *XEM_DOI_SOAT)
        hom_nay = timezone.localdate()
        ds_tt = list(
            ThanhToan.objects.filter(
                Q(trang_thai=TT.CHUA_NOP)
                | Q(
                    don__ds_hang_muc__loai=HangMucSuaChua.Loai.VAT_TU,
                    don__ds_hang_muc__nguoi_ung=HangMucSuaChua.NguoiUng.THO,
                )
            )
            .exclude(phieu_doi_soat__trang_thai=PT.DA_NOP)
            .select_related("tho", "phieu_doi_soat")
            .distinct()
        )
        vat_tu = _vat_tu_ung_theo_don(tt.don_id for tt in ds_tt)
        bang: dict[int, TongHopTho] = {}
        for d in _dong(ds_tt, vat_tu):
            tt = d.thanh_toan
            th = bang.setdefault(tt.tho_id, TongHopTho(tho=tt.tho, ma_tho=tt.tho.ma_tho))
            th.tien_chua_nop += d.tien_thu
            th.vat_tu_chua_hoan += d.tien_vat_tu
            if tt.phieu_doi_soat_id is None:
                th.so_dong_cho_doi_soat += 1
            if tt.trang_thai == TT.CHUA_NOP:
                so_ngay = (hom_nay - timezone.localdate(tt.thoi_diem_thu)).days
                th.so_ngay_cu_nhat = max(so_ngay, th.so_ngay_cu_nhat or 0)
        for th in bang.values():
            th.so_phai_nop = th.tien_chua_nop - th.vat_tu_chua_hoan
        for p in PhieuDoiSoat.objects.filter(tho_id__in=bang, trang_thai=PT.NHAP):
            bang[p.tho_id].phieu_nhap.append(p)
        return sorted(bang.values(), key=lambda th: (-th.so_phai_nop, th.tho.ho_ten))

    @staticmethod
    def danh_sach_phieu(nguoi_dung, tho=None, gioi_han: int = 50):
        """Kế toán/QT/GĐ: mọi phiếu; thợ: chỉ phiếu của mình (SPEC 3.1)."""
        qs = PhieuDoiSoat.objects.select_related("tho", "nguoi_lap")
        if not co_vai_tro(nguoi_dung, *XEM_DOI_SOAT):
            kiem_tra_vai_tro(nguoi_dung, THO)
            qs = qs.filter(tho__nguoi_dung=nguoi_dung)
        elif tho is not None:
            qs = qs.filter(tho=tho)
        return list(qs[:gioi_han])

    @staticmethod
    def lay_phieu(nguoi_dung, ma: str) -> PhieuDoiSoat:
        """Thợ hỏi phiếu của người khác → DoesNotExist (view trả 404, NFR04)."""
        qs = PhieuDoiSoat.objects.select_related("tho", "nguoi_lap")
        if not co_vai_tro(nguoi_dung, *XEM_DOI_SOAT):
            kiem_tra_vai_tro(nguoi_dung, THO)
            qs = qs.filter(tho__nguoi_dung=nguoi_dung)
        return qs.get(ma=ma)

    @staticmethod
    def dong_cua_phieu(phieu: PhieuDoiSoat) -> list[DongDoiSoat]:
        return _dong(phieu.ds_thanh_toan.select_related("don").order_by("thoi_diem_thu", "id"))

    @staticmethod
    def dong_co_the_them(phieu: PhieuDoiSoat) -> list[DongDoiSoat]:
        """Phiếu nháp: các khoản chưa vào phiếu nào trong kỳ của phiếu — để kế toán chọn lại."""
        if phieu.trang_thai != PT.NHAP:
            return []
        return _dong(DoiSoatDAO._ung_vien(phieu.tho_id, phieu.tu_ngay, phieu.den_ngay).select_related("don"))

    @staticmethod
    def _ung_vien(tho_id, tu_ngay: date, den_ngay: date):
        ids = ThanhToan.objects.filter(
            _cho_doi_soat(tho_id), thoi_diem_thu__date__gte=tu_ngay, thoi_diem_thu__date__lte=den_ngay
        ).values("pk")
        return ThanhToan.objects.filter(pk__in=ids).order_by("thoi_diem_thu", "id")

    # ------------------------------------------------------------ ghi

    @staticmethod
    def _cap_nhat_tong(phieu: PhieuDoiSoat) -> None:
        ds = DoiSoatDAO.dong_cua_phieu(phieu)
        phieu.tong_tien_thu = sum(d.tien_thu for d in ds)
        phieu.tong_vat_tu_ung = sum(d.tien_vat_tu for d in ds)
        phieu.so_phai_nop = phieu.tong_tien_thu - phieu.tong_vat_tu_ung
        phieu.save(update_fields=["tong_tien_thu", "tong_vat_tu_ung", "so_phai_nop", "cap_nhat_luc"])

    @staticmethod
    def _tong(phieu: PhieuDoiSoat) -> dict:
        return {
            "tong_tien_thu": phieu.tong_tien_thu,
            "tong_vat_tu_ung": phieu.tong_vat_tu_ung,
            "so_phai_nop": phieu.so_phai_nop,
            "trang_thai": phieu.trang_thai,
        }

    @staticmethod
    def _khoa_phieu(phieu: PhieuDoiSoat, *trang_thai) -> PhieuDoiSoat:
        phieu = PhieuDoiSoat.objects.select_for_update().select_related("tho").get(pk=phieu.pk)
        if trang_thai and phieu.trang_thai not in trang_thai:
            raise ValidationError(
                f"Phiếu {phieu.ma} đang “{phieu.get_trang_thai_display()}”, không làm được thao tác này."
            )
        return phieu

    @staticmethod
    def ky_mac_dinh(tho, den_ngay: date | None = None) -> tuple[date, date]:
        """Mặc định: từ sau phiếu gần nhất đến hôm nay; còn khoản cũ hơn chưa đối soát (đã bỏ chọn) thì lùi về
        ngày của khoản cũ nhất (A-79)."""
        den = den_ngay or timezone.localdate()
        moc = []
        cuoi = PhieuDoiSoat.objects.filter(tho=tho).order_by("-den_ngay").first()
        if cuoi:
            moc.append(cuoi.den_ngay + timedelta(days=1))
        cu_nhat = (
            ThanhToan.objects.filter(pk__in=ThanhToan.objects.filter(_cho_doi_soat(tho.pk)).values("pk"))
            .order_by("thoi_diem_thu")
            .values_list("thoi_diem_thu", flat=True)
            .first()
        )
        if cu_nhat:
            moc.append(timezone.localdate(cu_nhat))
        return min([*moc, den]), den

    @staticmethod
    def lap_phieu(
        nguoi_dung, tho: Tho, tu_ngay: date | None = None, den_ngay: date | None = None, ghi_chu: str = ""
    ) -> PhieuDoiSoat:
        """Lập phiếu NHAP cho một thợ và kỳ: gom mọi ThanhToan chưa vào phiếu nào trong kỳ (khóa dòng)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        with transaction.atomic():
            tho = Tho.objects.select_for_update().get(
                pk=tho.pk
            )  # tuần tự hóa lập phiếu của một thợ (mã, dòng)
            mac_dinh_tu, mac_dinh_den = DoiSoatDAO.ky_mac_dinh(tho, den_ngay)
            tu, den = tu_ngay or mac_dinh_tu, den_ngay or mac_dinh_den
            if den < tu:
                raise ValidationError({"den_ngay": "Đến ngày phải sau từ ngày."})
            ds_tt = list(
                DoiSoatDAO._ung_vien(tho.pk, tu, den)
                .select_for_update(of=("self",))
                .filter(phieu_doi_soat=None)
            )
            if not ds_tt:
                raise ValidationError(
                    f"{tho.ho_ten} không có khoản nào cần đối soát từ {tu:%d/%m/%Y} đến {den:%d/%m/%Y}."
                )
            tien_to = f"DS-{den:%y%m}-{tho.ma_tho}-"
            n = PhieuDoiSoat.objects.filter(ma__startswith=tien_to).count() + 1
            phieu = PhieuDoiSoat.objects.create(
                ma=f"{tien_to}{n}",
                tho=tho,
                tu_ngay=tu,
                den_ngay=den,
                nguoi_lap=nguoi_dung,
                ghi_chu=ghi_chu.strip(),
            )
            ThanhToan.objects.filter(pk__in=[tt.pk for tt in ds_tt]).update(
                phieu_doi_soat=phieu, cap_nhat_luc=timezone.now()
            )
            DoiSoatDAO._cap_nhat_tong(phieu)
            ghi_nhat_ky(
                nguoi_dung,
                "LAP_PHIEU_DOI_SOAT",
                phieu,
                du_lieu_sau={
                    "tho": tho.pk,
                    "tu_ngay": tu,
                    "den_ngay": den,
                    "thanh_toan": [tt.pk for tt in ds_tt],
                    **DoiSoatDAO._tong(phieu),
                },
            )
        return phieu

    @staticmethod
    def cap_nhat_dong(nguoi_dung, phieu: PhieuDoiSoat, ds_thanh_toan_id) -> PhieuDoiSoat:
        """Phiếu NHAP: giữ đúng các dòng được chọn (bỏ chọn dòng chưa đối chiếu được; chọn lại khoản trong kỳ)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        chon = {int(i) for i in ds_thanh_toan_id}
        with transaction.atomic():
            phieu = DoiSoatDAO._khoa_phieu(phieu, PT.NHAP)
            hien_co = set(phieu.ds_thanh_toan.values_list("pk", flat=True))
            them = chon - hien_co
            hop_le = set(
                DoiSoatDAO._ung_vien(phieu.tho_id, phieu.tu_ngay, phieu.den_ngay)
                .filter(pk__in=them)
                .select_for_update(of=("self",))
                .filter(phieu_doi_soat=None)
                .values_list("pk", flat=True)
            )
            if them - hop_le:
                raise ValidationError(
                    "Có khoản đã nằm trong phiếu khác hoặc không thuộc thợ/kỳ của phiếu này."
                )
            ThanhToan.objects.filter(pk__in=hien_co - chon).update(
                phieu_doi_soat=None, cap_nhat_luc=timezone.now()
            )
            ThanhToan.objects.filter(pk__in=them).update(phieu_doi_soat=phieu, cap_nhat_luc=timezone.now())
            truoc = DoiSoatDAO._tong(phieu)
            DoiSoatDAO._cap_nhat_tong(phieu)
            ghi_nhat_ky(
                nguoi_dung,
                "SUA_DONG_DOI_SOAT",
                phieu,
                {"thanh_toan": sorted(hien_co), **truoc},
                {"thanh_toan": sorted(chon), **DoiSoatDAO._tong(phieu)},
            )
        return phieu

    @staticmethod
    def chot(nguoi_dung, phieu: PhieuDoiSoat) -> PhieuDoiSoat:
        """NHAP → DA_CHOT: khóa các dòng (không sửa được nữa), báo thợ số phải nộp."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        with transaction.atomic():
            phieu = DoiSoatDAO._khoa_phieu(phieu, PT.NHAP)
            if not phieu.ds_thanh_toan.exists():
                raise ValidationError("Phiếu chưa có dòng nào.")
            DoiSoatDAO._cap_nhat_tong(phieu)
            phieu.trang_thai = PT.DA_CHOT
            phieu.save(update_fields=["trang_thai", "cap_nhat_luc"])
            ghi_nhat_ky(
                nguoi_dung, "CHOT_PHIEU_DOI_SOAT", phieu, {"trang_thai": PT.NHAP}, DoiSoatDAO._tong(phieu)
            )
            DichVuThongBao.gui(
                phieu.tho.nguoi_dung,
                f"Phiếu đối soát {phieu.ma} đã chốt",
                (
                    f"Phải nộp {phieu.so_phai_nop:,} đ".replace(",", ".")
                    if phieu.so_phai_nop >= 0
                    else f"Công ty trả bạn {-phieu.so_phai_nop:,} đ".replace(",", ".")
                ),
                "/tho/doi-soat/",
            )
        return phieu

    @staticmethod
    def xac_nhan_da_nop(nguoi_dung, phieu: PhieuDoiSoat) -> PhieuDoiSoat:
        """DA_CHOT → DA_NOP; mọi ThanhToan CHUA_NOP trong phiếu → DA_NOP (SPEC 6.4). Ghi nhật ký tiền (NFR06)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        with transaction.atomic():
            phieu = DoiSoatDAO._khoa_phieu(phieu, PT.DA_CHOT)
            ds = list(
                phieu.ds_thanh_toan.select_for_update()
                .filter(trang_thai=TT.CHUA_NOP)
                .values_list("pk", flat=True)
            )
            ThanhToan.objects.filter(pk__in=ds).update(trang_thai=TT.DA_NOP, cap_nhat_luc=timezone.now())
            phieu.trang_thai = PT.DA_NOP
            phieu.xac_nhan_luc = timezone.now()
            phieu.save(update_fields=["trang_thai", "xac_nhan_luc", "cap_nhat_luc"])
            ghi_nhat_ky(
                nguoi_dung,
                "XAC_NHAN_NOP_TIEN",
                phieu,
                {"trang_thai": PT.DA_CHOT},
                {**DoiSoatDAO._tong(phieu), "thanh_toan_da_nop": ds},
            )
            DichVuThongBao.gui(
                phieu.tho.nguoi_dung, f"Phiếu {phieu.ma}: kế toán đã xác nhận", "Đã nộp đủ.", "/tho/doi-soat/"
            )
        return phieu

    @staticmethod
    def mo_lai(nguoi_dung, phieu: PhieuDoiSoat, ly_do: str) -> PhieuDoiSoat:
        """“Mở lại phiếu” (SPEC 6.4): DA_CHOT/DA_NOP → NHAP; ThanhToan DA_NOP → CHUA_NOP. Bắt buộc lý do."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        if not (ly_do or "").strip():
            raise ValidationError({"ly_do": "Nhập lý do mở lại phiếu."})
        with transaction.atomic():
            phieu = DoiSoatDAO._khoa_phieu(phieu, PT.DA_CHOT, PT.DA_NOP)
            truoc = DoiSoatDAO._tong(phieu)
            ds = list(phieu.ds_thanh_toan.filter(trang_thai=TT.DA_NOP).values_list("pk", flat=True))
            ThanhToan.objects.filter(pk__in=ds).update(trang_thai=TT.CHUA_NOP, cap_nhat_luc=timezone.now())
            phieu.trang_thai = PT.NHAP
            phieu.xac_nhan_luc = None
            phieu.save(update_fields=["trang_thai", "xac_nhan_luc", "cap_nhat_luc"])
            ghi_nhat_ky(
                nguoi_dung,
                "MO_LAI_PHIEU_DOI_SOAT",
                phieu,
                truoc,
                {**DoiSoatDAO._tong(phieu), "ly_do": ly_do.strip(), "thanh_toan_ve_chua_nop": ds},
            )
        return phieu

    @staticmethod
    def huy_nhap(nguoi_dung, phieu: PhieuDoiSoat) -> None:
        """Bỏ phiếu NHAP: trả các khoản về chờ đối soát rồi xóa phiếu (chỉ phiếu nháp)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DOI_SOAT)
        with transaction.atomic():
            phieu = DoiSoatDAO._khoa_phieu(phieu, PT.NHAP)
            ds = list(phieu.ds_thanh_toan.values_list("pk", flat=True))
            phieu.ds_thanh_toan.update(phieu_doi_soat=None, cap_nhat_luc=timezone.now())
            ghi_nhat_ky(
                nguoi_dung, "HUY_PHIEU_DOI_SOAT", phieu, {**DoiSoatDAO._tong(phieu), "thanh_toan": ds}
            )
            phieu.delete()
