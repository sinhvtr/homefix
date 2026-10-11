"""Dữ liệu mẫu hư cấu — phần đơn (SPEC 14.4): ~60 đơn trải đều mọi trạng thái trong 30 ngày qua và hôm nay,
có đơn bảo hành, có phiếu đối soát — để thử mọi màn hình và báo cáo.

Đặt ở app báo cáo (tầng trên cùng) vì phải đi qua DAO của mọi app nghiệp vụ (A-82). Mọi đơn đi đúng luồng nghiệp vụ
(tiếp nhận → chốt lịch → cử thợ → thợ nhận → đến nơi → báo giá → hoàn thành …) nên trạng thái, nhật ký, thanh toán,
phiếu bảo hành luôn nhất quán; chỉ dời mốc thời gian (lúc thu tiền, phiếu bảo hành) về ngày làm việc trong quá khứ.
"""

import io
import random
from datetime import datetime, time, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from apps.bao_hanh.dao import BaoHanhDAO
from apps.bao_hanh.models import PhieuBaoHanh
from apps.bao_hanh.tac_vu import dong_don_het_bao_hanh
from apps.danh_muc.du_lieu_mau import TIEN_TO_SDT, xoa_danh_muc
from apps.danh_muc.models import DichVu, KhachHang, Tho
from apps.don_sua_chua.dao import DonSuaChuaDAO, HienTruongDAO
from apps.don_sua_chua.models import AnhHienTruong, DonSuaChua
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_chinh.dao import DoiSoatDAO
from apps.tai_chinh.models import PhieuDoiSoat, ThanhToan
from apps.tai_khoan.models import NguoiDung, VaiTro
from apps.thuc_hien.dao import DonSuaChuaDAO as HoanThanhDAO
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO, ThoDAO, TiepNhanDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong

MO_TA = {
    "DIEU_HOA": ["Điều hòa chảy nước", "Điều hòa không mát", "Điều hòa kêu to", "Bảo dưỡng định kỳ"],
    "MAY_GIAT": ["Máy giặt không vắt", "Máy giặt rung mạnh", "Máy giặt không xả"],
    "TU_LANH": ["Tủ lạnh không lạnh ngăn dưới", "Tủ lạnh đóng tuyết", "Tủ lạnh kêu to"],
    "BINH_NONG_LANH": ["Bình nóng lạnh không nóng", "Bình rò nước ở van", "Vệ sinh cặn bình"],
    "DIEN_NUOC": ["Rò nước dưới bồn rửa", "Chập điện ổ cắm bếp", "Nhảy aptomat liên tục"],
    "KHAC": ["Kiểm tra thiết bị"],
}
VAT_TU = [
    ("Gas R32", 1, 450_000, 280_000),
    ("Tụ máy nén", 1, 250_000, 150_000),
    ("Van xả", 1, 180_000, 90_000),
    ("Ống đồng (m)", 2, 120_000, 70_000),
    ("Thanh đốt 2500W", 1, 350_000, 210_000),
    ("Aptomat 32A", 1, 160_000, 95_000),
]
LY_DO_HUY = ["Khách tự sửa được", "Khách đi vắng, hẹn sau", "Khách đổi ý, mua máy mới"]
HINH_THUC = ["TIEN_MAT"] * 5 + ["CK_TAI_KHOAN_THO"] * 3 + ["CK_TAI_KHOAN_CONG_TY"] * 2


class _NapDon:
    def __init__(self, hat_giong: int):
        self.rng = random.Random(hat_giong)
        mau = NguoiDung.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT).order_by("so_dien_thoai")
        self.ds_tong_dai = list(mau.filter(vai_tro=VaiTro.TONG_DAI))
        self.ke_toan = mau.filter(vai_tro=VaiTro.KE_TOAN).first()
        self.khach = list(
            KhachHang.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT).prefetch_related(
                "ds_dia_chi__ds_thiet_bi"
            )
        )
        self.dich_vu = list(DichVu.objects.filter(dang_ap_dung=True).order_by("ma"))
        self.khung = cau_hinh("KHUNG_GIO")
        self.hom_nay = timezone.localdate()
        self.dem = {"don": 0, "anh": 0}

    # ------------------------------------------------------------ tiện ích

    def tong_dai(self):
        return self.rng.choice(self.ds_tong_dai)

    def _anh(self) -> SimpleUploadedFile:
        mau = tuple(self.rng.randint(60, 220) for _ in range(3))
        dem = io.BytesIO()
        Image.new("RGB", (320, 240), mau).save(dem, format="JPEG")
        self.dem["anh"] += 1
        return SimpleUploadedFile("anh.jpg", dem.getvalue(), content_type="image/jpeg")

    def tiep_nhan(self, so_ngay_truoc: int, chot_lich=True, nhom=None, ngay_hen_lech=0) -> DonSuaChua:
        """Tạo đơn qua TiepNhanDAO (UC02): khách, địa chỉ, thiết bị mẫu; dịch vụ đúng loại thiết bị."""
        kh = self.rng.choice(self.khach)
        dc = self.rng.choice(list(kh.ds_dia_chi.all()))
        ds_tb = list(dc.ds_thiet_bi.all())
        tb = self.rng.choice(ds_tb) if ds_tb else None
        hop = [dv for dv in self.dich_vu if (tb is None or dv.loai_thiet_bi == tb.loai_thiet_bi)]
        if nhom:
            hop = [dv for dv in hop if dv.nhom_dich_vu == nhom] or [
                dv for dv in self.dich_vu if dv.nhom_dich_vu == nhom
            ]
            if tb and hop[0].loai_thiet_bi != tb.loai_thiet_bi:
                tb = None
        dv = self.rng.choice(hop or self.dich_vu)
        ngay = self.hom_nay - timedelta(days=so_ngay_truoc)
        luc = timezone.make_aware(
            datetime.combine(ngay, time(self.rng.randint(7, 11), self.rng.randint(0, 59)))
        )
        if so_ngay_truoc == 0:
            luc = min(luc, timezone.now() - timedelta(minutes=self.rng.randint(5, 50)))
        du_lieu = {
            "so_dien_thoai": kh.so_dien_thoai,
            "dia_chi_id": dc.pk,
            "thiet_bi_ids": [tb.pk] if tb else [],
            "dich_vu_yeu_cau": dv,
            "kenh_tiep_nhan": self.rng.choice(["DIEN_THOAI"] * 4 + ["ZALO", "GIAM_DOC_CHUYEN"]),
            "mo_ta_su_co": self.rng.choice(MO_TA.get(dv.loai_thiet_bi, MO_TA["KHAC"])),
            "khung_gio_mong_muon": ""
            if chot_lich
            else self.rng.choice(["Chiều nay", "Cuối tuần", "Sau 17h"]),
            "ngay_tiep_nhan": luc,
        }
        if chot_lich:
            du_lieu["ngay_hen"] = ngay + timedelta(days=ngay_hen_lech)
            du_lieu["khung_gio"] = self.rng.choice(self.khung)
        self.dem["don"] += 1
        return TiepNhanDAO.tiep_nhan(self.tong_dai(), du_lieu).don

    def cu_tho(self, don: DonSuaChua):
        """UC04/UC07: gửi đề nghị cho thợ gợi ý đầu bảng (BR04) và thợ nhận. Không có thợ phù hợp → None.
        Đôi khi gửi thêm một thợ khác và người này từ chối — cho báo cáo tỷ lệ nhận/từ chối."""
        don = DonSuaChua.objects.get(pk=don.pk)
        hop = [g.tho for g in ThoDAO.goi_y_tho(don) if g.phu_hop][:3]
        if not hop:
            return None
        tho = self.rng.choice(hop)
        khac = next((t for t in hop if t != tho), None) if self.rng.random() < 0.35 else None
        td = self.tong_dai()
        if tho.pk not in PhanCongDAO.gui_de_nghi(td, don, [tho.pk] + ([khac.pk] if khac else [])):
            return None
        if khac is not None and (
            pc_khac := don.ds_phan_cong.filter(tho=khac, trang_thai="CHO_PHAN_HOI").first()
        ):
            PhanCongDAO.tu_choi(khac.nguoi_dung, pc_khac.pk, self.rng.choice(["BAN", "XA"]))
        PhanCongDAO.nhan_viec(tho.nguoi_dung, don.ds_phan_cong.get(tho=tho, trang_thai="CHO_PHAN_HOI").pk)
        # dời mốc đề nghị về lúc tiếp nhận (+ vài chục phút) để báo cáo "tiếp nhận → có thợ" có nghĩa
        giao = min(don.ngay_tiep_nhan + timedelta(minutes=self.rng.randint(3, 40)), timezone.now())
        for pc in don.ds_phan_cong.all():
            phan_hoi = giao + timedelta(minutes=self.rng.randint(1, 14))
            PhanCong.objects.filter(pk=pc.pk).update(
                thoi_diem_giao=giao, han_phan_hoi=giao + timedelta(minutes=15), thoi_diem_phan_hoi=phan_hoi
            )
        return tho

    def den_noi_va_bao_gia(self, don, tho, vat_tu=True, duyet=True):
        nd = tho.nguoi_dung
        HienTruongDAO.tho_den_noi(nd, DonSuaChua.objects.get(pk=don.pk))
        don = DonSuaChua.objects.get(pk=don.pk)
        if don.trang_thai == "CHO_DUYET_GIA":
            HienTruongDAO.them_hang_muc(nd, don, {"loai": "CONG", "dich_vu": don.dich_vu_yeu_cau})
        if vat_tu and self.rng.random() < 0.6:
            mo_ta, sl, ban, mua = self.rng.choice(VAT_TU)
            HienTruongDAO.them_hang_muc(
                nd,
                don,
                {
                    "loai": "VAT_TU",
                    "mo_ta": mo_ta,
                    "so_luong": sl,
                    "don_gia_thuc_te": ban,
                    "gia_mua": mua,
                    "co_hoa_don": self.rng.random() < 0.4,
                    "nguoi_ung": "THO" if self.rng.random() < 0.8 else "CONG_TY",
                },
            )
        don = DonSuaChua.objects.get(pk=don.pk)
        if don.trang_thai == "CHO_DUYET_GIA" and duyet:
            HienTruongDAO.khach_duyet_gia(nd, don, don.khach_hang.ho_ten)
        return DonSuaChua.objects.get(pk=don.pk)

    def hoan_thanh(self, don, tho):
        nd = tho.nguoi_dung
        for _ in range(self.rng.choice([1, 1, 2])):
            HienTruongDAO.luu_anh(nd, don, self._anh())
        don = DonSuaChua.objects.get(pk=don.pk)
        if don.loai_don == "BAO_HANH":
            DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(nd, don, self.rng.choice(["TAY_NGHE", "VAT_TU"]))
            don = DonSuaChua.objects.get(pk=don.pk)
        tong = don.tong_tien
        hinh_thuc = self.rng.choice(HINH_THUC)
        so_tien, ly_do = tong, ""
        if tong and self.rng.random() < 0.08:
            so_tien, ly_do = tong - 20_000, "Khách xin bớt tiền lẻ"
        kq = HoanThanhDAO.hoan_thanh(nd, don, so_tien, hinh_thuc, ly_do)
        # dời mốc về ngày làm việc của đơn (lúc kết thúc khung giờ hẹn)
        lich = kq.don.lich_hieu_luc
        luc = lich.ket_thuc if lich else kq.don.ngay_tiep_nhan
        ThanhToan.objects.filter(pk=kq.thanh_toan.pk).update(thoi_diem_thu=luc)
        if kq.phieu_bao_hanh:
            p = kq.phieu_bao_hanh
            lech = p.ngay_bat_dau - timezone.localdate(luc)
            het_han_moi = p.ngay_het_han - lech
            PhieuBaoHanh.objects.filter(pk=p.pk).update(
                ngay_bat_dau=p.ngay_bat_dau - lech,
                ngay_het_han=het_han_moi,
                dieu_kien=p.dieu_kien.replace(f"{p.ngay_het_han:%d/%m/%Y}", f"{het_han_moi:%d/%m/%Y}"),
            )
        return kq.don

    def tron_luong(self, so_ngay_truoc, nhom=None):
        """Đơn đi trọn đến HOAN_THANH; không cử được thợ thì hủy (đơn quá khứ không thể còn chờ)."""
        don = self.tiep_nhan(so_ngay_truoc, nhom=nhom)
        tho = self.cu_tho(don)
        if tho is None:
            DonSuaChuaDAO.huy(self.tong_dai(), don, "Không có thợ phù hợp, khách hẹn dịp khác")
            return None
        return self.hoan_thanh(self.den_noi_va_bao_gia(don, tho), tho)

    # ------------------------------------------------------------ kịch bản

    def chay(self) -> dict:
        r = self.rng
        # 1) Quá khứ 1–30 ngày: đơn đã làm xong (vệ sinh quá 7 ngày sẽ được tác vụ BR05 đóng → DA_DONG)
        xong = []
        for i in range(30):
            d = self.tron_luong(r.randint(1, 30), nhom="SUA_CHUA_THAY_VAT_TU" if i % 3 == 0 else None)
            if d:
                xong.append(d)
        # 2) Quá khứ: hủy theo nhiều đường — khách hủy (T14), từ chối báo giá (T13), hết lượt nhắc (BR08, T5)
        for _ in range(3):
            d = self.tiep_nhan(r.randint(1, 20))
            DonSuaChuaDAO.huy(self.tong_dai(), d, r.choice(LY_DO_HUY))
        d = self.tiep_nhan(r.randint(2, 15), nhom="SUA_CHUA_THAY_VAT_TU")
        tho = self.cu_tho(d)
        if tho:
            d = self.den_noi_va_bao_gia(d, tho, duyet=False)
            HienTruongDAO.khach_tu_choi_gia(tho.nguoi_dung, d, "Giá cao")
        d = self.tiep_nhan(r.randint(5, 25), chot_lich=False)
        for _ in range(4):
            DonSuaChuaDAO.nhac_xac_nhan(self.tong_dai(), DonSuaChua.objects.get(pk=d.pk))

        # 3) Bảo hành (UC11): đơn sửa chữa còn hạn → đơn bảo hành ở các chặng khác nhau
        goc_bh = [d for d in xong if d.nhom_dich_vu == "SUA_CHUA_THAY_VAT_TU"][:3]
        for i, goc in enumerate(goc_bh):
            goc = DonSuaChua.objects.get(pk=goc.pk)
            ngay = self.hom_nay + timedelta(days=0 if i < 2 else 1)
            bh = BaoHanhDAO.tao_don_bao_hanh(
                self.tong_dai(),
                goc,
                mo_ta_su_co="Khách báo lỗi cũ tái diễn",
                ngay_hen=ngay,
                khung_gio=self.khung[i % len(self.khung)],
            )
            self.dem["don"] += 1
            if i == 2:
                continue  # chờ cử thợ → đơn gốc DANG_BAO_HANH
            tho = self.cu_tho(bh)
            if tho and i == 0:  # bảo hành xong → đơn gốc về HOAN_THANH (T17)
                self.hoan_thanh(self.den_noi_va_bao_gia(bh, tho, vat_tu=False), tho)

        # 4) Hôm nay / sắp tới: mọi trạng thái đang xử lý
        for _ in range(5):  # CHO_XAC_NHAN_LICH (một số đã nhắc)
            d = self.tiep_nhan(0, chot_lich=False)
            if r.random() < 0.4:
                DonSuaChuaDAO.nhac_xac_nhan(self.tong_dai(), d)
        cho_cu = [self.tiep_nhan(0, ngay_hen_lech=r.choice([0, 1])) for _ in range(6)]
        DonSuaChuaDAO.danh_dau_chua_cu_duoc(
            self.tong_dai(), cho_cu[0], "Không có thợ điện nước rảnh khung giờ này"
        )
        for d in cho_cu[1:3]:  # đề nghị hết 15 phút không ai nhận (BR02) → thẻ "Cần cử lại" trên bảng đơn
            hop = [g.tho for g in ThoDAO.goi_y_tho(DonSuaChua.objects.get(pk=d.pk)) if g.phu_hop][:1]
            if hop and PhanCongDAO.gui_de_nghi(self.tong_dai(), d, [hop[0].pk]):
                giao = timezone.now() - timedelta(minutes=r.randint(20, 40))
                PhanCong.objects.filter(don=d, trang_thai="CHO_PHAN_HOI").update(
                    trang_thai="QUA_HAN", thoi_diem_giao=giao, han_phan_hoi=giao + timedelta(minutes=15)
                )
        for _ in range(5):  # DA_CO_THO
            self.cu_tho(self.tiep_nhan(0))
        for i in range(3):  # CHO_DUYET_GIA (một đơn vượt ngưỡng chờ tổng đài gọi xác nhận)
            d = self.tiep_nhan(0, nhom="SUA_CHUA_THAY_VAT_TU")
            tho = self.cu_tho(d)
            if tho is None:
                continue
            d = self.den_noi_va_bao_gia(d, tho, duyet=False)
            if i == 0:
                HienTruongDAO.them_hang_muc(
                    tho.nguoi_dung,
                    d,
                    {
                        "loai": "VAT_TU",
                        "mo_ta": "Máy nén thay thế",
                        "so_luong": 1,
                        "don_gia_thuc_te": 2_600_000,
                        "gia_mua": 1_900_000,
                    },
                )
                HienTruongDAO.khach_duyet_gia(
                    tho.nguoi_dung, DonSuaChua.objects.get(pk=d.pk), d.khach_hang.ho_ten
                )
        for _ in range(4):  # DANG_SUA
            d = self.tiep_nhan(0)
            tho = self.cu_tho(d)
            if tho:
                self.den_noi_va_bao_gia(d, tho)

        # 5) BR05: đóng đơn đã hết hạn bảo hành (T18)
        da_dong = dong_don_het_bao_hanh()["da_dong"]

        # 6) Đối soát (UC12): ba thợ thu nhiều nhất — một phiếu đã nộp, một đã chốt, một nháp
        bang = DoiSoatDAO.tong_hop_theo_tho(self.ke_toan)
        phieu = []
        for i, th in enumerate(bang[:3]):
            p = DoiSoatDAO.lap_phieu(self.ke_toan, th.tho)
            if i <= 1:
                p = DoiSoatDAO.chot(self.ke_toan, p)
            if i == 0:
                p = DoiSoatDAO.xac_nhan_da_nop(self.ke_toan, p)
            phieu.append(p.ma)
        return {**self.dem, "da_dong": da_dong, "phieu_doi_soat": len(phieu)}


def nap_don_mau(hat_giong: int = 2026) -> dict:
    """Gọi sau `nap_danh_muc`. Một giao dịch: lỗi giữa chừng không để lại dữ liệu dở dang."""
    with transaction.atomic():
        ket_qua = _NapDon(hat_giong).chay()
        ghi_nhat_ky(None, "NAP_DU_LIEU_MAU", "DonSuaChua:mau", du_lieu_sau=ket_qua)
    return ket_qua


def xoa_du_lieu_mau() -> dict[str, int]:
    """Xóa đơn mẫu cùng thanh toán, phiếu đối soát, phiếu bảo hành, ảnh (cả tệp), rồi danh mục mẫu."""
    with transaction.atomic():
        don = DonSuaChua.objects.filter(khach_hang__so_dien_thoai__startswith=TIEN_TO_SDT)
        tho = Tho.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT)
        tt = ThanhToan.objects.filter(don__in=don)
        ket_qua = {
            "phieu_doi_soat": PhieuDoiSoat.objects.filter(tho__in=tho).count(),
            "thanh_toan": tt.count(),
        }
        anh = AnhHienTruong.objects.filter(don__in=don)
        tep = [(a.tep.storage, a.tep.name) for a in anh] + [
            (t.anh_chung_tu.storage, t.anh_chung_tu.name) for t in tt.exclude(anh_chung_tu="")
        ]
        ket_qua["anh"] = len(tep)
        tt.update(phieu_doi_soat=None)
        PhieuDoiSoat.objects.filter(tho__in=tho).delete()
        tt.delete()
        PhieuBaoHanh.objects.filter(don__in=don).delete()
        ket_qua.update(
            xoa_danh_muc()
        )  # xóa đơn (kéo theo hạng mục, lịch, phân công, bản ghi ảnh) và danh mục
        # Tệp ảnh chỉ xóa khi giao dịch đã commit — lỗi giữa chừng không làm mất tệp của bản ghi còn lại
        transaction.on_commit(lambda: [kho.delete(ten) for kho, ten in tep])
    return ket_qua
