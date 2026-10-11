"""DAO tiếp nhận (UC02) và lịch hẹn (UC03). Ghi: kiểm quyền, transaction.atomic(), khóa dòng đơn, ghi nhật ký."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.danh_muc.dao import DiaChiDAO, KhachHangDAO, ThietBiDAO
from apps.danh_muc.dao import ThoDAO as DanhMucThoDAO
from apps.danh_muc.models import DiaChi, KhachHang, ThietBi, Tho
from apps.don_sua_chua.dao import GHI_DON, DonSuaChuaDAO, ghi_doi_trang_thai
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt
from apps.tai_khoan.models import VaiTro
from apps.tai_khoan.phan_quyen import kiem_tra_vai_tro

from .models import LichHen, PhanCong
from .thong_bao_dieu_phoi import bao_tho, bao_tong_dai, gui_de_nghi_nhan_viec

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
        if don.trang_thai == T.DA_CO_THO and don.tho_id:
            # UC03 [ĐX]: báo thợ lịch mới để xác nhận lại; trùng lịch thì tổng đài rút việc (T8)
            bao_tho(
                PhanCong.objects.select_related("tho__nguoi_dung").get(
                    don=don, trang_thai=PhanCong.TrangThai.DA_NHAN
                ),
                f"Đổi lịch {don.ma_don}",
                f"Lịch mới: {moi.khung_gio}. Nếu không đi được, bấm “Báo bận / trả việc”.",
                f"/tho/don/{don.ma_don}/",
            )
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
                ngay_tiep_nhan=du_lieu.get("ngay_tiep_nhan"),
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


# ====================================================================== UC04, UC05 — điều phối, gợi ý thợ

DANG_BAN = (T.DA_CO_THO, T.CHO_DUYET_GIA, T.DANG_SUA)  # đơn chiếm lịch của thợ (BR04)
TINH_VIEC_TRONG_NGAY = (*DANG_BAN, T.HOAN_THANH)
LY_DO_DA_CO_THO = "Đơn đã có thợ nhận"


@dataclass
class GoiYTho:
    """Một dòng trong danh sách gợi ý (UC05) — mọi tiêu chí hiển thị minh bạch."""

    tho: Tho
    phu_hop: bool
    ly_do_loai: list[str]
    phu_trach_khu_vuc: bool
    khu_vuc: list[str]
    so_viec_trong_ngay: int
    khung_gio_ban: list[str]
    du_kien_ranh_luc: datetime | None
    ty_le_nhan_30_ngay: float | None
    lan_giao_gan_nhat: datetime | None
    da_tu_choi: bool
    da_qua_han: bool
    dang_cho_phan_hoi: bool
    la_tho_don_goc: bool


class ThoDAO(DanhMucThoDAO):
    """Mở rộng ThoDAO của danh mục với goi_y_tho (tên theo slide Tuần 12). Đặt ở app điều phối vì cần
    DonSuaChua, LichHen, PhanCong — gói danh mục ở tầng dưới không được import các lớp này."""

    @staticmethod
    def goi_y_tho(don: DonSuaChua, lich: LichHen | None = None) -> list[GoiYTho]:
        """BR04 + thuật toán xếp hạng UC05. Thợ phù hợp lên trước theo thứ tự xếp hạng; thợ bị loại xếp sau
        kèm lý do. Số câu SQL cố định (≤ 5) bất kể số thợ/đơn (NFR01)."""
        lich = lich or don.lich_hieu_luc
        if lich is None:
            raise ValidationError("Đơn chưa có lịch hẹn hiệu lực.")
        bay_gio = timezone.now()
        dem = timedelta(minutes=cau_hinh("DEM_DI_CHUYEN_PHUT"))
        dv = don.dich_vu_yeu_cau
        ngay = timezone.localdate(lich.bat_dau)

        # (1) Thợ đang hoạt động + khu vực, kỹ năng gộp mảng — một câu SQL
        ds_tho = list(
            Tho.objects.filter(nguoi_dung__is_active=True).annotate(
                kv_id=ArrayAgg("khu_vuc_phu_trach__id", distinct=True),
                kv_ten=ArrayAgg("khu_vuc_phu_trach__ten", distinct=True),
                kn_id=ArrayAgg("ky_nang__id", distinct=True),
                kn_loai=ArrayAgg("ky_nang__loai_thiet_bi", distinct=True),
            )
        )
        # (2) Lịch hiệu lực của các đơn có thợ: trong ngày hẹn, hoặc giao với khung giờ (kể cả đệm di chuyển)
        ban: dict[int, list[dict]] = {}
        for dong in (
            LichHen.objects.filter(
                trang_thai=LichHen.TrangThai.HIEU_LUC,
                don__tho__isnull=False,
                don__trang_thai__in=TINH_VIEC_TRONG_NGAY,
            )
            .filter(
                Q(bat_dau__date=ngay) | Q(bat_dau__lt=lich.ket_thuc + dem, ket_thuc__gt=lich.bat_dau - dem)
            )
            .exclude(don=don)
            .values("don__tho_id", "don__ma_don", "don__trang_thai", "bat_dau", "ket_thuc")
            .order_by("bat_dau")
        ):
            ban.setdefault(dong["don__tho_id"], []).append(dong)
        # (3) Thống kê đề nghị: 30 ngày gần nhất và với chính đơn này
        moc_30 = bay_gio - timedelta(days=30)
        tk = {
            d["tho_id"]: d
            for d in PhanCong.objects.filter(Q(thoi_diem_giao__gte=moc_30) | Q(don=don))
            .values("tho_id")
            .annotate(
                tong=Count("id", filter=Q(thoi_diem_giao__gte=moc_30)),
                nhan=Count("id", filter=Q(thoi_diem_giao__gte=moc_30, trang_thai=PhanCong.TrangThai.DA_NHAN)),
                lan_cuoi=Max("thoi_diem_giao"),
                tu_choi=Count("id", filter=Q(don=don, trang_thai=PhanCong.TrangThai.TU_CHOI)),
                qua_han=Count("id", filter=Q(don=don, trang_thai=PhanCong.TrangThai.QUA_HAN)),
                dang_cho=Count("id", filter=Q(don=don, trang_thai=PhanCong.TrangThai.CHO_PHAN_HOI)),
            )
            .order_by()
        }
        tho_don_goc = (
            DonSuaChua.objects.filter(pk=don.don_goc_id).values_list("tho_id", flat=True).first()
            if don.don_goc_id
            else None
        )

        ket_qua = []
        for tho in ds_tho:
            kv_id = [x for x in tho.kv_id if x is not None]
            ly_do = []
            if not tho.dang_nhan_viec:
                ly_do.append("Tắt nhận việc")
            if tho.nghi_den and tho.nghi_den > lich.bat_dau:
                ly_do.append(f"Đang nghỉ đến {timezone.localtime(tho.nghi_den):%d/%m %H:%M}")
            if dv.pk not in tho.kn_id and dv.loai_thiet_bi not in tho.kn_loai:
                ly_do.append("Sai nghề")
            lich_ban = ban.get(tho.pk, [])
            for b in lich_ban:
                if (
                    b["don__trang_thai"] in DANG_BAN
                    and b["bat_dau"] < lich.ket_thuc + dem
                    and b["ket_thuc"] + dem > lich.bat_dau
                ):
                    ly_do.append(f"Trùng lịch {b['don__ma_don']}")
            trong_ngay = [b for b in lich_ban if timezone.localdate(b["bat_dau"]) == ngay]
            con_ban = [b for b in trong_ngay if b["don__trang_thai"] in DANG_BAN]
            t = tk.get(tho.pk, {})
            ket_qua.append(
                GoiYTho(
                    tho=tho,
                    phu_hop=not ly_do,
                    ly_do_loai=ly_do,
                    phu_trach_khu_vuc=don.dia_chi.khu_vuc_id in kv_id,
                    khu_vuc=sorted(x for x in tho.kv_ten if x),
                    so_viec_trong_ngay=len(trong_ngay),
                    khung_gio_ban=[
                        f"{timezone.localtime(b['bat_dau']):%H:%M}-{timezone.localtime(b['ket_thuc']):%H:%M} "
                        f"{b['don__ma_don']}"
                        for b in con_ban
                    ],
                    du_kien_ranh_luc=(max(b["ket_thuc"] for b in con_ban) + dem) if con_ban else None,
                    ty_le_nhan_30_ngay=(t["nhan"] / t["tong"]) if t.get("tong") else None,
                    lan_giao_gan_nhat=t.get("lan_cuoi"),
                    da_tu_choi=bool(t.get("tu_choi")),
                    da_qua_han=bool(t.get("qua_han")),
                    dang_cho_phan_hoi=bool(t.get("dang_cho")),
                    la_tho_don_goc=tho_don_goc is not None and tho_don_goc == tho.pk,
                )
            )
        rat_cu = datetime.min.replace(tzinfo=bay_gio.tzinfo)
        ket_qua.sort(
            key=lambda g: (
                not g.phu_hop,
                not g.phu_trach_khu_vuc,  # (a) đúng khu vực trước
                g.so_viec_trong_ngay,  # (b) ít việc trong ngày trước — chia đều việc
                g.lan_giao_gan_nhat or rat_cu,  # (c) lâu chưa được giao trước
                g.tho.hinh_thuc != Tho.HinhThuc.CHINH_THUC,  # (d) chính thức trước cộng tác viên [ĐX]
                g.tho.ho_ten,
            )
        )
        return ket_qua


def tien_cong_du_kien(don: DonSuaChua) -> int:
    """Chụp từ bảng giá lúc gửi đề nghị: vệ sinh = đơn giá × số thiết bị (≥ 1); sửa chữa = giá “từ…”."""
    dv = don.dich_vu_yeu_cau
    if dv.nhom_dich_vu == dv.NhomDichVu.VE_SINH_BAO_DUONG:
        return dv.don_gia_tham_khao * max(1, don.thiet_bi.count())
    return dv.don_gia_tham_khao


class PhanCongDAO:
    @staticmethod
    def _huy_de_nghi_dang_cho(don: DonSuaChua, tru_pk=None, ly_do: str = LY_DO_DA_CO_THO) -> list[PhanCong]:
        ds = list(
            PhanCong.objects.select_for_update(of=("self",))
            .select_related("tho__nguoi_dung")
            .filter(don=don, trang_thai__in=[PhanCong.TrangThai.CHO_PHAN_HOI, PhanCong.TrangThai.QUA_HAN])
            .exclude(pk=tru_pk)
        )
        bay_gio = timezone.now()
        for pc in ds:
            pc.trang_thai = PhanCong.TrangThai.DA_HUY
            pc.ghi_chu = ly_do
            pc.thoi_diem_phan_hoi = pc.thoi_diem_phan_hoi or bay_gio
            pc.save(update_fields=["trang_thai", "ghi_chu", "thoi_diem_phan_hoi", "cap_nhat_luc"])
        return ds

    @staticmethod
    def giao_viec(pc: PhanCong) -> bool:
        """Ghi PhanCong (+ đổi trạng thái đơn khi thợ đã đồng ý qua điện thoại) trong MỘT giao dịch.
        Chỉ khi trả True mới gửi thông báo đề nghị cho thợ (SPEC UC04). BR01: người giao phải là tổng đài/quản trị."""
        kiem_tra_vai_tro(pc.nguoi_giao, *GHI_DON)
        with transaction.atomic():
            don = (
                DonSuaChua.objects.select_for_update(of=("self",))
                .select_related("dich_vu_yeu_cau", "dia_chi")
                .get(pk=pc.don_id)
            )
            if don.trang_thai != T.CHO_CU_THO or don.tho_id is not None:
                return False
            goi_y = next((g for g in ThoDAO.goi_y_tho(don) if g.tho.pk == pc.tho_id), None)
            if goi_y is None or not goi_y.phu_hop or goi_y.dang_cho_phan_hoi:
                return False
            bay_gio = timezone.now()
            pc.don = don
            pc.thoi_diem_giao = bay_gio
            pc.tien_cong_du_kien = tien_cong_du_kien(don)
            if pc.giao_qua_dien_thoai:  # luồng 3a [ĐX]: tạo thẳng DA_NHAN, bắt buộc ghi chú
                if not (pc.ghi_chu or "").strip():
                    raise ValidationError({"ghi_chu": "Ghi chú bắt buộc khi thợ đồng ý qua điện thoại."})
                pc.trang_thai = PhanCong.TrangThai.DA_NHAN
                pc.han_phan_hoi = pc.thoi_diem_phan_hoi = bay_gio
                pc.save()
                don.giao_cho_tho(pc)
                ds_huy = PhanCongDAO._huy_de_nghi_dang_cho(don, tru_pk=pc.pk)
                ghi_nhat_ky(
                    pc.nguoi_giao,
                    "CU_THO_QUA_DIEN_THOAI",
                    don,
                    du_lieu_sau={"phan_cong": pc.pk, "tho": pc.tho_id, "ghi_chu": pc.ghi_chu},
                )
                ghi_doi_trang_thai(pc.nguoi_giao, don)
            else:
                pc.trang_thai = PhanCong.TrangThai.CHO_PHAN_HOI
                pc.han_phan_hoi = bay_gio + timedelta(minutes=cau_hinh("THOI_HAN_PHAN_HOI_PHUT"))
                pc.save()
                ds_huy = []
                ghi_nhat_ky(
                    pc.nguoi_giao,
                    "GUI_DE_NGHI",
                    don,
                    du_lieu_sau={"phan_cong": pc.pk, "tho": pc.tho_id, "han_phan_hoi": pc.han_phan_hoi},
                )
        # Sau giao dịch: thông báo (bản ghi trong ứng dụng ngay; kênh ngoài chạy nền sau commit)
        if pc.giao_qua_dien_thoai:
            bao_tho(
                pc,
                f"Đã giao việc {don.ma_don}",
                "Tổng đài ghi nhận bạn đã đồng ý qua điện thoại.",
                f"/tho/don/{don.ma_don}/",
            )
        else:
            gui_de_nghi_nhan_viec(pc)
        for khac in ds_huy:
            bao_tho(khac, f"Đề nghị {don.ma_don} đã hủy", LY_DO_DA_CO_THO)
        return True

    @staticmethod
    def gui_de_nghi(nguoi_dung, don: DonSuaChua, ds_tho_id: list[int]) -> list[int]:
        """UC04 bước 3–4: gửi đề nghị cho một hoặc nhiều thợ. Nhật ký ghi ai, lúc nào, gửi cho những thợ nào (NFR06)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        da_gui = []
        with transaction.atomic():
            for tho_id in dict.fromkeys(ds_tho_id):
                if PhanCongDAO.giao_viec(PhanCong(don=don, tho_id=tho_id, nguoi_giao=nguoi_dung)):
                    da_gui.append(tho_id)
            if da_gui:
                ghi_nhat_ky(nguoi_dung, "CU_THO", don, du_lieu_sau={"gui_cho_tho": da_gui})
        return da_gui

    @staticmethod
    def _cua_tho(nguoi_dung, pc_id) -> PhanCong:
        """NFR04: thợ chỉ thao tác trên đề nghị của mình."""
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        pc = PhanCong.objects.select_related("tho").filter(pk=pc_id, tho__nguoi_dung=nguoi_dung).first()
        if pc is None:
            raise PermissionDenied("Không có đề nghị này.")
        return pc

    @staticmethod
    def nhan_viec(nguoi_dung, pc_id: int) -> tuple[bool, str]:
        """UC07 — BR03: khóa dòng đơn, người bấm trước được nhận; người đến sau nhận “Đơn đã có thợ nhận”.
        Đề nghị đã QUA_HAN mà đơn vẫn chờ cử thợ → vẫn cho nhận, ghi nhật ký “nhận muộn” [ĐX]."""
        pc = PhanCongDAO._cua_tho(nguoi_dung, pc_id)
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update().get(pk=pc.don_id)
            pc = (
                PhanCong.objects.select_for_update(of=("self",))
                .select_related("tho__nguoi_dung", "nguoi_giao")
                .get(pk=pc.pk)
            )
            if pc.trang_thai not in (PhanCong.TrangThai.CHO_PHAN_HOI, PhanCong.TrangThai.QUA_HAN):
                # Người đến sau (đề nghị vừa bị hủy vì thợ khác nhận trước) → “Đơn đã có thợ nhận” (BR03)
                if pc.trang_thai == PhanCong.TrangThai.DA_HUY and don.tho_id is not None:
                    return False, LY_DO_DA_CO_THO
                return False, "Đề nghị không còn hiệu lực."
            if don.trang_thai != T.CHO_CU_THO or don.tho_id is not None:
                pc.trang_thai = PhanCong.TrangThai.DA_HUY
                pc.ghi_chu = LY_DO_DA_CO_THO
                pc.thoi_diem_phan_hoi = timezone.now()
                pc.save(update_fields=["trang_thai", "ghi_chu", "thoi_diem_phan_hoi", "cap_nhat_luc"])
                return False, LY_DO_DA_CO_THO
            nhan_muon = pc.trang_thai == PhanCong.TrangThai.QUA_HAN
            pc.trang_thai = PhanCong.TrangThai.DA_NHAN
            pc.thoi_diem_phan_hoi = timezone.now()
            pc.save(update_fields=["trang_thai", "thoi_diem_phan_hoi", "cap_nhat_luc"])
            don.giao_cho_tho(pc)
            ds_huy = PhanCongDAO._huy_de_nghi_dang_cho(don, tru_pk=pc.pk)
            ghi_nhat_ky(
                nguoi_dung,
                "NHAN_VIEC",
                don,
                du_lieu_sau={"phan_cong": pc.pk, "tho": pc.tho_id, "nhan_muon": nhan_muon},
            )
            ghi_doi_trang_thai(nguoi_dung, don)
        tieu_de = f"{pc.tho.ho_ten} đã nhận {don.ma_don}" + (" (nhận muộn)" if nhan_muon else "")
        bao_tong_dai(pc.nguoi_giao, don, tieu_de)
        for khac in ds_huy:
            bao_tho(khac, f"Đề nghị {don.ma_don} đã hủy", LY_DO_DA_CO_THO)
        return True, "Đã nhận việc."

    @staticmethod
    def tu_choi(nguoi_dung, pc_id: int, ly_do: str, ghi_chu: str = "") -> None:
        pc = PhanCongDAO._cua_tho(nguoi_dung, pc_id)
        if ly_do not in PhanCong.LyDoTuChoi.values:
            raise ValidationError("Chọn lý do từ chối.")
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update().get(pk=pc.don_id)
            pc = (
                PhanCong.objects.select_for_update(of=("self",))
                .select_related("tho", "nguoi_giao")
                .get(pk=pc.pk)
            )
            if pc.trang_thai != PhanCong.TrangThai.CHO_PHAN_HOI:
                raise ValidationError("Đề nghị không còn chờ phản hồi.")
            pc.trang_thai = PhanCong.TrangThai.TU_CHOI
            pc.ly_do_tu_choi = ly_do
            pc.ghi_chu = ghi_chu
            pc.thoi_diem_phan_hoi = timezone.now()
            pc.save(
                update_fields=["trang_thai", "ly_do_tu_choi", "ghi_chu", "thoi_diem_phan_hoi", "cap_nhat_luc"]
            )
            ghi_nhat_ky(nguoi_dung, "TU_CHOI_VIEC", don, du_lieu_sau={"phan_cong": pc.pk, "ly_do": ly_do})
            can_cu_lai = PhanCongDAO.can_cu_lai(don)
        bao_tong_dai(
            pc.nguoi_giao, don, f"{pc.tho.ho_ten} từ chối {don.ma_don}", pc.get_ly_do_tu_choi_display()
        )
        if can_cu_lai:
            bao_tong_dai(
                pc.nguoi_giao, don, f"Cần cử lại {don.ma_don}", "Không còn đề nghị nào đang chờ thợ phản hồi."
            )

    # ------------------------------------------------------------ đọc phía thợ (NFR04: chỉ của mình)

    @staticmethod
    def de_nghi_dang_cho_cua_tho(nguoi_dung) -> list[PhanCong]:
        """Đề nghị còn nhận được: đang chờ, hoặc quá hạn mà đơn vẫn chờ cử thợ (được nhận muộn — A-13)."""
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        return list(
            PhanCong.objects.filter(tho__nguoi_dung=nguoi_dung)
            .filter(
                Q(trang_thai=PhanCong.TrangThai.CHO_PHAN_HOI)
                | Q(
                    trang_thai=PhanCong.TrangThai.QUA_HAN, don__trang_thai=T.CHO_CU_THO, don__tho__isnull=True
                )
            )
            .select_related("don__dich_vu_yeu_cau", "don__dia_chi__khu_vuc")
            .prefetch_related("don__ds_lich_hen")
            .order_by("han_phan_hoi")
        )

    @staticmethod
    def lay_de_nghi_cua_tho(nguoi_dung, pc_id: int) -> PhanCong:
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        return (
            PhanCong.objects.select_related("don__dich_vu_yeu_cau", "don__dia_chi__khu_vuc")
            .filter(tho__nguoi_dung=nguoi_dung)
            .get(pk=pc_id)
        )

    @staticmethod
    def viec_cua_tho(nguoi_dung) -> list[DonSuaChua]:
        """Đơn thợ đang phụ trách (đã nhận, chưa xong), theo giờ hẹn."""
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        ds = list(
            DonSuaChua.objects.filter(tho__nguoi_dung=nguoi_dung, trang_thai__in=DANG_BAN)
            .select_related("dich_vu_yeu_cau", "dia_chi__khu_vuc", "khach_hang")
            .prefetch_related("ds_lich_hen")
        )
        xa = timezone.now() + timedelta(days=3650)
        ds.sort(key=lambda d: d.lich_hieu_luc.bat_dau if d.lich_hieu_luc else xa)
        return ds

    @staticmethod
    def lay_don_cua_tho(nguoi_dung, ma_don: str) -> DonSuaChua:
        """NFR04: thợ chỉ xem SĐT, địa chỉ khách của đơn mình đang phụ trách (đã nhận). Khác → DoesNotExist (404)."""
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        return (
            DonSuaChua.objects.select_related("khach_hang", "dia_chi__khu_vuc", "dich_vu_yeu_cau")
            .prefetch_related("thiet_bi", "ds_hang_muc")
            .get(ma_don=ma_don, tho__nguoi_dung=nguoi_dung, trang_thai__in=DANG_BAN)
        )

    @staticmethod
    def lich_su_tai_dia_chi(don: DonSuaChua) -> list[DonSuaChua]:
        """Lịch sử thiết bị/đơn tại cùng địa chỉ (UC07) — chỉ gọi sau khi lay_don_cua_tho đã kiểm quyền."""
        return list(
            DonSuaChua.objects.filter(dia_chi_id=don.dia_chi_id)
            .exclude(pk=don.pk)
            .exclude(trang_thai=T.DA_HUY)
            .select_related("dich_vu_yeu_cau")
            .order_by("-ngay_tiep_nhan")[:10]
        )

    @staticmethod
    def can_cu_lai(don: DonSuaChua) -> bool:
        """BR02: đơn vẫn chờ cử thợ mà hết đề nghị đang chờ phản hồi."""
        return (
            don.trang_thai == T.CHO_CU_THO
            and don.tho_id is None
            and not PhanCong.objects.filter(don=don, trang_thai=PhanCong.TrangThai.CHO_PHAN_HOI).exists()
        )

    @staticmethod
    def thu_hoi(nguoi_dung, pc_id: int) -> None:
        """Tổng đài thu hồi một đề nghị đang chờ → DA_HUY."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        with transaction.atomic():
            pc = (
                PhanCong.objects.select_for_update(of=("self",))
                .select_related("don", "tho__nguoi_dung")
                .get(pk=pc_id)
            )
            if pc.trang_thai != PhanCong.TrangThai.CHO_PHAN_HOI:
                raise ValidationError("Chỉ thu hồi được đề nghị đang chờ phản hồi.")
            pc.trang_thai = PhanCong.TrangThai.DA_HUY
            pc.ghi_chu = "Tổng đài thu hồi đề nghị"
            pc.thoi_diem_phan_hoi = timezone.now()
            pc.save(update_fields=["trang_thai", "ghi_chu", "thoi_diem_phan_hoi", "cap_nhat_luc"])
            ghi_nhat_ky(
                nguoi_dung, "THU_HOI_DE_NGHI", pc.don, du_lieu_sau={"phan_cong": pc.pk, "tho": pc.tho_id}
            )
        bao_tho(pc, f"Đề nghị {pc.don.ma_don} đã thu hồi", "Tổng đài đã thu hồi đề nghị này.")

    @staticmethod
    def tra_viec(nguoi_dung, don: DonSuaChua, ly_do: str) -> None:
        """T8: thợ báo bận / tổng đài rút việc (chỉ trước khi thợ “Đã đến nơi”)."""
        la_tho = nguoi_dung.vai_tro == VaiTro.THO
        if not la_tho:
            kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        if not (ly_do or "").strip():
            raise ValidationError({"ly_do": "Nhập lý do."})
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update().get(pk=don.pk)
            pc = (
                PhanCong.objects.select_for_update(of=("self",))
                .select_related("tho__nguoi_dung", "nguoi_giao")
                .filter(don=don, trang_thai=PhanCong.TrangThai.DA_NHAN)
                .first()
            )
            if pc is None or don.trang_thai != T.DA_CO_THO:
                raise ValidationError("Đơn không ở trạng thái có thể trả việc.")
            if la_tho and pc.tho.nguoi_dung_id != nguoi_dung.pk:
                raise PermissionDenied("Không phải việc của bạn.")
            pc.trang_thai = PhanCong.TrangThai.DA_HUY
            pc.ghi_chu = f"{'Thợ trả việc' if la_tho else 'Tổng đài rút việc'}: {ly_do.strip()}"
            pc.save(update_fields=["trang_thai", "ghi_chu", "cap_nhat_luc"])
            don.huy_phan_cong_hien_tai(ly_do)
            ghi_nhat_ky(
                nguoi_dung,
                "TRA_VIEC" if la_tho else "RUT_VIEC",
                don,
                du_lieu_sau={"tho": pc.tho_id, "ly_do": ly_do},
            )
            ghi_doi_trang_thai(nguoi_dung, don, ly_do)
        if la_tho:
            bao_tong_dai(pc.nguoi_giao, don, f"{pc.tho.ho_ten} trả việc {don.ma_don}", ly_do)
        else:
            bao_tho(pc, f"Việc {don.ma_don} đã bị rút", ly_do)

    @staticmethod
    def kiem_tra_qua_han(bay_gio=None) -> dict[str, int]:
        """BR02 — tác vụ mỗi phút: đề nghị quá hạn → QUA_HAN, báo tổng đài đã giao; đơn hết đề nghị đang chờ mà
        vẫn chờ cử thợ → thông báo “Cần cử lại”. Lũy đẳng."""
        bay_gio = bay_gio or timezone.now()
        ket_qua = {"qua_han": 0, "can_cu_lai": 0}
        don_lien_quan: dict[int, tuple] = {}
        with transaction.atomic():
            for pc in (
                PhanCong.objects.select_for_update(skip_locked=True, of=("self",))
                .select_related("don__dich_vu_yeu_cau", "don__dia_chi__khu_vuc", "tho", "nguoi_giao")
                .filter(trang_thai=PhanCong.TrangThai.CHO_PHAN_HOI, han_phan_hoi__lt=bay_gio)
            ):
                pc.trang_thai = PhanCong.TrangThai.QUA_HAN
                pc.save(update_fields=["trang_thai", "cap_nhat_luc"])
                ghi_nhat_ky(
                    None, "DE_NGHI_QUA_HAN", pc.don, du_lieu_sau={"phan_cong": pc.pk, "tho": pc.tho_id}
                )
                bao_tong_dai(pc.nguoi_giao, pc.don, f"{pc.tho.ho_ten} quá hạn phản hồi {pc.don.ma_don}")
                ket_qua["qua_han"] += 1
                don_lien_quan[pc.don_id] = (pc.don, pc.nguoi_giao)
            for don, nguoi_giao in don_lien_quan.values():
                if PhanCongDAO.can_cu_lai(don):
                    bao_tong_dai(
                        nguoi_giao, don, f"Cần cử lại {don.ma_don}", "Hết hạn phản hồi, chưa thợ nào nhận."
                    )
                    ket_qua["can_cu_lai"] += 1
        return ket_qua
