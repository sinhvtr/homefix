"""BaoCaoDAO — báo cáo vận hành và doanh thu (UC14). Chỉ đọc.

Mốc thời gian (A-85, A-86):
- "tiếp nhận trong kỳ" theo `DonSuaChua.ngay_tiep_nhan`;
- "hoàn thành trong kỳ" theo `ThanhToan.thoi_diem_thu` (mỗi đơn hoàn thành có đúng một ThanhToan, tạo ở T15);
- hủy, không cử được thợ: tính trên các đơn **tiếp nhận** trong kỳ;
- "có thợ" = lúc thợ nhận đề nghị (`PhanCong.thoi_diem_phan_hoi` của phân công DA_NHAN);
- đề nghị nhận việc theo `PhanCong.thoi_diem_giao`.
"""

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.db.models import Count, Min, Q, Sum
from django.utils import timezone

from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_chinh.models import ThanhToan
from apps.tai_khoan.phan_quyen import GD, KT, QT, co_vai_tro, kiem_tra_vai_tro
from apps.tiep_nhan_dieu_phoi.models import PhanCong

XEM_BAO_CAO = (QT, KT, GD)  # SPEC 3.1 — Báo cáo: QT R, KT R (tài chính), GĐ R
XEM_VAN_HANH = (QT, GD)  # kế toán chỉ xem phần tài chính
MOC_KHONG_CU_DUOC = 0.15  # hiện trạng: ~15% đơn không cử được thợ [SRS]
MOC_CONG_NO = (12_000_000, 15_000_000)  # hiện trạng: công nợ thợ 12–15 triệu [SRS]
PHUT_CO_THO = 30

KY = {
    "hom_nay": "Hôm nay",
    "7_ngay": "7 ngày",
    "thang_nay": "Tháng này",
    "tuy_chon": "Tùy chọn",
}


@dataclass(frozen=True)
class KyBaoCao:
    ma: str
    tu: date
    den: date

    @property
    def nhan(self) -> str:
        return f"{self.tu:%d/%m/%Y} – {self.den:%d/%m/%Y}"

    @property
    def bat_dau(self) -> datetime:
        return timezone.make_aware(datetime.combine(self.tu, time.min))

    @property
    def ket_thuc(self) -> datetime:
        """Mốc mở: 00:00 ngày sau `den` (giờ Việt Nam)."""
        return timezone.make_aware(datetime.combine(self.den + timedelta(days=1), time.min))

    def cac_ngay(self) -> list[date]:
        return [self.tu + timedelta(days=i) for i in range((self.den - self.tu).days + 1)]


def chon_ky(
    ma: str | None, tu: date | None = None, den: date | None = None, hom_nay: date | None = None
) -> KyBaoCao:
    """Mặc định 7 ngày (A-86). Tùy chọn thiếu ngày → về mặc định; đảo ngược thì đổi chỗ."""
    hom_nay = hom_nay or timezone.localdate()
    if ma == "hom_nay":
        return KyBaoCao(ma, hom_nay, hom_nay)
    if ma == "thang_nay":
        return KyBaoCao(ma, hom_nay.replace(day=1), hom_nay)
    if ma == "tuy_chon" and tu and den:
        tu, den = min(tu, den), max(tu, den)
        return KyBaoCao(ma, tu, den)
    return KyBaoCao("7_ngay", hom_nay - timedelta(days=6), hom_nay)


@dataclass
class DongTyLe:
    ten: str
    tu_so: int
    mau_so: int

    @property
    def ty_le(self) -> float | None:
        return self.tu_so / self.mau_so if self.mau_so else None


@dataclass
class BaoCao:
    ky: KyBaoCao
    xem_van_hanh: bool
    # vận hành
    so_tiep_nhan: int = 0
    so_hoan_thanh: int = 0
    so_huy: int = 0
    huy_theo_ly_do: list[tuple[str, int]] = field(default_factory=list)
    khong_cu_duoc: DongTyLe | None = None
    trung_vi_phut_co_tho: float | None = None
    co_tho_trong_30_phut: DongTyLe | None = None
    lam_lai: DongTyLe | None = None
    lam_lai_theo_tho: list[DongTyLe] = field(default_factory=list)
    de_nghi_theo_tho: list[dict] = field(default_factory=list)
    # tài chính
    doanh_thu: int = 0
    doanh_thu_theo_ngay: list[tuple[date, int]] = field(default_factory=list)
    doanh_thu_theo_dich_vu: list[tuple[str, int, int]] = field(default_factory=list)  # (tên, số đơn, tiền)
    doanh_thu_theo_tho: list[tuple[str, int, int]] = field(default_factory=list)
    doanh_thu_theo_khu_vuc: list[tuple[str, int, int]] = field(default_factory=list)
    cong_no_hien_tai: int = 0
    cong_no_theo_tho: list[tuple[str, int]] = field(default_factory=list)
    don_theo_ngay: list[tuple[date, int, int]] = field(default_factory=list)  # (ngày, tiếp nhận, hoàn thành)

    @property
    def moc_khong_cu_duoc(self) -> float:
        return MOC_KHONG_CU_DUOC

    @property
    def moc_cong_no(self) -> tuple[int, int]:
        return MOC_CONG_NO


def _ma(ma_don: str) -> str:
    return f"DonSuaChua:{ma_don}"


class BaoCaoDAO:
    @staticmethod
    def lap(nguoi_dung, ky: KyBaoCao) -> BaoCao:
        kiem_tra_vai_tro(nguoi_dung, *XEM_BAO_CAO)
        bc = BaoCao(ky=ky, xem_van_hanh=co_vai_tro(nguoi_dung, *XEM_VAN_HANH))
        tiep_nhan = DonSuaChua.objects.filter(ngay_tiep_nhan__gte=ky.bat_dau, ngay_tiep_nhan__lt=ky.ket_thuc)
        # Hoàn thành trong kỳ: một ThanhToan mỗi đơn (T15) — lấy đơn + thời điểm thu
        tt_ky = ThanhToan.objects.filter(thoi_diem_thu__gte=ky.bat_dau, thoi_diem_thu__lt=ky.ket_thuc)
        hoan_thanh = list(
            tt_ky.select_related("don__dich_vu_yeu_cau", "don__dia_chi__khu_vuc", "tho").order_by(
                "thoi_diem_thu"
            )
        )
        bc.so_tiep_nhan = tiep_nhan.count()
        bc.so_hoan_thanh = len({tt.don_id for tt in hoan_thanh})
        BaoCaoDAO._tai_chinh(bc, ky, hoan_thanh, tiep_nhan)
        if bc.xem_van_hanh:
            BaoCaoDAO._van_hanh(bc, ky, tiep_nhan, hoan_thanh)
        return bc

    # ------------------------------------------------------------ tài chính

    @staticmethod
    def _tai_chinh(bc: BaoCao, ky: KyBaoCao, hoan_thanh: list[ThanhToan], tiep_nhan) -> None:
        theo_ngay, dv, tho, kv = (
            Counter(),
            defaultdict(lambda: [0, 0]),
            defaultdict(lambda: [0, 0]),
            defaultdict(lambda: [0, 0]),
        )
        da_tinh = set()
        for tt in hoan_thanh:
            d = tt.don
            if d.pk in da_tinh:
                continue
            da_tinh.add(d.pk)
            tien = d.tong_tien_phai_thu or 0
            bc.doanh_thu += tien
            theo_ngay[timezone.localdate(tt.thoi_diem_thu)] += tien
            for bang, khoa in (
                (dv, d.dich_vu_yeu_cau.ten_dich_vu),
                (tho, tt.tho.ho_ten),
                (kv, d.dia_chi.khu_vuc.ten),
            ):
                bang[khoa][0] += 1
                bang[khoa][1] += tien
        bc.doanh_thu_theo_ngay = [(n, theo_ngay[n]) for n in ky.cac_ngay()]

        def sap(bang):
            return sorted(((k, v[0], v[1]) for k, v in bang.items()), key=lambda x: (-x[2], x[0]))

        bc.doanh_thu_theo_dich_vu, bc.doanh_thu_theo_tho, bc.doanh_thu_theo_khu_vuc = (
            sap(dv),
            sap(tho),
            sap(kv),
        )
        no = (
            ThanhToan.objects.filter(trang_thai=ThanhToan.TrangThai.CHUA_NOP)
            .values("tho__ho_ten")
            .annotate(tong=Sum("so_tien"))
            .order_by("-tong", "tho__ho_ten")
        )
        bc.cong_no_theo_tho = [(d["tho__ho_ten"], d["tong"]) for d in no]
        bc.cong_no_hien_tai = sum(t for _, t in bc.cong_no_theo_tho)
        nhan_ngay = Counter(timezone.localdate(n) for n in tiep_nhan.values_list("ngay_tiep_nhan", flat=True))
        xong_ngay = Counter(
            timezone.localdate(t) for t in {tt.don_id: tt.thoi_diem_thu for tt in hoan_thanh}.values()
        )
        bc.don_theo_ngay = [(n, nhan_ngay[n], xong_ngay[n]) for n in ky.cac_ngay()]

    # ------------------------------------------------------------ vận hành

    @staticmethod
    def _van_hanh(bc: BaoCao, ky: KyBaoCao, tiep_nhan, hoan_thanh: list[ThanhToan]) -> None:
        ds_don = list(
            tiep_nhan.values(
                "pk", "ma_don", "trang_thai", "ly_do_huy", "ngay_tiep_nhan", "canh_bao_chua_cu_duoc"
            )
        )
        ma_trong_ky = [_ma(d["ma_don"]) for d in ds_don]
        # Hủy theo lý do
        huy = [d for d in ds_don if d["trang_thai"] == TrangThaiDon.DA_HUY]
        bc.so_huy = len(huy)
        bc.huy_theo_ly_do = Counter((d["ly_do_huy"] or "(không ghi)").strip() for d in huy).most_common()
        # Không cử được thợ: từng gắn cờ (nhật ký hoặc cờ hiện tại) hoặc bị hủy khi đang chờ cử thợ
        nk = NhatKyThaoTac.objects.filter(doi_tuong__in=ma_trong_ky)
        tung_gan_co = set(nk.filter(hanh_dong="CHUA_CU_DUOC_THO").values_list("doi_tuong", flat=True))
        huy_khi_cho = set(
            nk.filter(
                hanh_dong="DOI_TRANG_THAI",
                du_lieu_truoc__trang_thai=TrangThaiDon.CHO_CU_THO,
                du_lieu_sau__trang_thai=TrangThaiDon.DA_HUY,
            ).values_list("doi_tuong", flat=True)
        )
        khong_cu = (
            {_ma(d["ma_don"]) for d in ds_don if d["canh_bao_chua_cu_duoc"]} | tung_gan_co | huy_khi_cho
        )
        bc.khong_cu_duoc = DongTyLe("Đơn không cử được thợ", len(khong_cu), len(ds_don))
        # Tiếp nhận → có thợ: lúc thợ nhận đề nghị đầu tiên còn hiệu lực (PhanCong DA_NHAN)
        co_tho = dict(
            PhanCong.objects.filter(
                don_id__in=[d["pk"] for d in ds_don], trang_thai=PhanCong.TrangThai.DA_NHAN
            )
            .values("don_id")
            .annotate(luc=Min("thoi_diem_phan_hoi"))
            .values_list("don_id", "luc")
        )
        phut = [
            max(0.0, (co_tho[d["pk"]] - d["ngay_tiep_nhan"]).total_seconds() / 60)
            for d in ds_don
            if co_tho.get(d["pk"])
        ]
        bc.trung_vi_phut_co_tho = statistics.median(phut) if phut else None
        bc.co_tho_trong_30_phut = DongTyLe(
            f"Có thợ trong {PHUT_CO_THO} phút", sum(p <= PHUT_CO_THO for p in phut), len(phut)
        )
        # Tỷ lệ làm lại = đơn bảo hành tạo trong kỳ / đơn thường hoàn thành trong kỳ (A-84); theo thợ làm đơn gốc
        bh = list(
            tiep_nhan.filter(loai_don=DonSuaChua.LoaiDon.BAO_HANH).values_list(
                "don_goc__tho__ho_ten", flat=True
            )
        )
        xong_thuong = {
            tt.don_id: tt.tho.ho_ten for tt in hoan_thanh if tt.don.loai_don == DonSuaChua.LoaiDon.THUONG
        }
        bc.lam_lai = DongTyLe("Tỷ lệ làm lại", len(bh), len(xong_thuong))
        tu, mau = Counter(t or "(chưa có thợ)" for t in bh), Counter(xong_thuong.values())
        bc.lam_lai_theo_tho = sorted(
            (DongTyLe(ten, tu[ten], mau[ten]) for ten in set(tu) | set(mau)),
            key=lambda d: (-(d.ty_le or 0), -d.tu_so, d.ten),
        )
        # Đề nghị nhận việc theo thợ (gửi trong kỳ)
        S = PhanCong.TrangThai
        dem = (
            PhanCong.objects.filter(thoi_diem_giao__gte=ky.bat_dau, thoi_diem_giao__lt=ky.ket_thuc)
            .values("tho_id", "tho__ho_ten")
            .annotate(
                tong=Count("id"),
                nhan=Count("id", filter=Q(trang_thai=S.DA_NHAN)),
                tu_choi=Count("id", filter=Q(trang_thai=S.TU_CHOI)),
                qua_han=Count("id", filter=Q(trang_thai=S.QUA_HAN)),
                huy=Count("id", filter=Q(trang_thai=S.DA_HUY)),
            )
            .order_by("tho__ho_ten")
        )
        bc.de_nghi_theo_tho = [
            {
                "tho": d["tho__ho_ten"],
                "tong": d["tong"],
                "nhan": d["nhan"],
                "tu_choi": d["tu_choi"],
                "qua_han": d["qua_han"],
                "huy": d["huy"],
                "ty_le_nhan": d["nhan"] / d["tong"] if d["tong"] else None,
            }
            for d in dem
        ]
