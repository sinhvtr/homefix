"""Dữ liệu mẫu hư cấu (SPEC 14.4) — phần danh mục (P1). Các giai đoạn sau bổ sung đơn, phiếu đối soát.

Nhận diện dữ liệu mẫu: mọi người dùng, thợ, khách mẫu có số điện thoại bắt đầu bằng TIEN_TO_SDT;
khu vực, dịch vụ mẫu theo mã trong KHU_VUC, DICH_VU (A-33).
"""

import random
from datetime import timedelta

from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.he_thong.models import NhatKyThaoTac
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.mat_khau import sinh_mat_khau_tam, sinh_pin
from apps.tai_khoan.models import NguoiDung, VaiTro

from .models import DiaChi, DichVu, KhachHang, KhuVuc, LoaiThietBi, ThietBi, Tho

TIEN_TO_SDT = "0900"

KHU_VUC = [
    ("BA_DINH", "Ba Đình"),
    ("HOAN_KIEM", "Hoàn Kiếm"),
    ("DONG_DA", "Đống Đa"),
    ("HAI_BA_TRUNG", "Hai Bà Trưng"),
    ("CAU_GIAY", "Cầu Giấy"),
    ("THANH_XUAN", "Thanh Xuân"),
    ("TAY_HO", "Tây Hồ"),
    ("HOANG_MAI", "Hoàng Mai"),
    ("LONG_BIEN", "Long Biên"),
    ("NAM_TU_LIEM", "Nam Từ Liêm"),
    ("BAC_TU_LIEM", "Bắc Từ Liêm"),
    ("HA_DONG", "Hà Đông"),
]

VS, SC = DichVu.NhomDichVu.VE_SINH_BAO_DUONG, DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU
L = LoaiThietBi
# (mã, tên, nhóm, loại thiết bị, đơn giá minh họa [ĐX], đơn vị tính)
DICH_VU = [
    ("VS-DH-TT", "Vệ sinh điều hòa treo tường", VS, L.DIEU_HOA, 150_000, "máy"),
    ("VS-DH-AT", "Vệ sinh điều hòa âm trần", VS, L.DIEU_HOA, 350_000, "máy"),
    ("VS-MG-CT", "Vệ sinh máy giặt cửa trên", VS, L.MAY_GIAT, 250_000, "máy"),
    ("VS-MG-CN", "Vệ sinh máy giặt cửa ngang", VS, L.MAY_GIAT, 350_000, "máy"),
    ("VS-TL", "Vệ sinh tủ lạnh", VS, L.TU_LANH, 200_000, "máy"),
    ("VS-BNL", "Vệ sinh bình nóng lạnh", VS, L.BINH_NONG_LANH, 200_000, "bình"),
    ("BD-DN", "Kiểm tra, bảo dưỡng điện nước", VS, L.DIEN_NUOC, 250_000, "lần"),
    ("SC-DH-GAS", "Nạp gas điều hòa", SC, L.DIEU_HOA, 350_000, "máy"),
    ("SC-DH-BOARD", "Sửa bo mạch điều hòa", SC, L.DIEU_HOA, 500_000, "máy"),
    ("SC-DH-BLOCK", "Sửa, thay block điều hòa", SC, L.DIEU_HOA, 800_000, "máy"),
    ("SC-DH-LAP", "Tháo lắp, di dời điều hòa", SC, L.DIEU_HOA, 400_000, "máy"),
    ("SC-MG-XA", "Sửa máy giặt không xả nước", SC, L.MAY_GIAT, 250_000, "lần"),
    ("SC-MG-VB", "Thay vòng bi máy giặt", SC, L.MAY_GIAT, 600_000, "máy"),
    ("SC-TL-GAS", "Nạp gas tủ lạnh", SC, L.TU_LANH, 400_000, "máy"),
    ("SC-TL-LANH", "Sửa tủ lạnh không lạnh", SC, L.TU_LANH, 300_000, "lần"),
    ("SC-BNL-DOT", "Thay thanh đốt bình nóng lạnh", SC, L.BINH_NONG_LANH, 300_000, "bình"),
    ("SC-BNL-RO", "Sửa bình nóng lạnh rò nước", SC, L.BINH_NONG_LANH, 250_000, "lần"),
    ("SC-DN-RO", "Sửa rò rỉ đường nước", SC, L.DIEN_NUOC, 200_000, "điểm"),
    ("SC-DN-CHAP", "Sửa chập điện, thay aptomat", SC, L.DIEN_NUOC, 150_000, "điểm"),
    ("SC-DN-OC", "Thay ổ cắm, công tắc", SC, L.DIEN_NUOC, 80_000, "điểm"),
]

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô", "Dương", "Lý"]
DEM_NAM = ["Văn", "Đức", "Minh", "Quang", "Hữu", "Thành"]
DEM_NU = ["Thị", "Thu", "Ngọc", "Thanh", "Phương"]
TEN_NAM = [
    "An",
    "Bình",
    "Cường",
    "Dũng",
    "Hải",
    "Hùng",
    "Khánh",
    "Long",
    "Nam",
    "Phúc",
    "Quân",
    "Sơn",
    "Tuấn",
]
TEN_NU = ["Anh", "Chi", "Dung", "Hà", "Hạnh", "Hoa", "Lan", "Linh", "Mai", "Ngọc", "Trang", "Yến"]
DUONG = [
    "Kim Mã",
    "Láng",
    "Giải Phóng",
    "Trần Duy Hưng",
    "Nguyễn Trãi",
    "Lạc Long Quân",
    "Minh Khai",
    "Tam Trinh",
    "Nguyễn Văn Cừ",
    "Mỹ Đình",
    "Phạm Văn Đồng",
    "Quang Trung",
    "Xã Đàn",
    "Hoàng Hoa Thám",
]
HANG = {
    L.DIEU_HOA: ["Daikin", "Panasonic", "LG", "Casper"],
    L.MAY_GIAT: ["Electrolux", "Samsung", "Toshiba", "LG"],
    L.TU_LANH: ["Hitachi", "Sharp", "Aqua", "Samsung"],
    L.BINH_NONG_LANH: ["Ariston", "Ferroli", "Rossi"],
    L.DIEN_NUOC: [""],
}
VI_TRI = ["Phòng khách", "Phòng ngủ 1", "Phòng ngủ 2", "Bếp", "Nhà tắm", "Ban công"]


class DaCoDuLieuMau(Exception):
    pass


def _ten(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return f"{rng.choice(HO)} {rng.choice(DEM_NAM)} {rng.choice(TEN_NAM)}"
    return f"{rng.choice(HO)} {rng.choice(DEM_NU)} {rng.choice(TEN_NU)}"


def _nguoi_dung(sdt: str, ho_ten: str, vai_tro: str, bi_mat: str) -> NguoiDung:
    nd = NguoiDung(username=sdt, so_dien_thoai=sdt, ho_ten=ho_ten, vai_tro=vai_tro, phai_doi_mat_khau=False)
    nd.set_password(bi_mat)
    nd.save()
    return nd


def nap_danh_muc(hat_giong: int = 2026) -> list[tuple[str, str, str, str]]:
    """Nạp danh mục mẫu. Trả danh sách (vai trò, họ tên, tên đăng nhập, mật khẩu/PIN) để in MỘT lần."""
    if NguoiDung.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT).exists():
        raise DaCoDuLieuMau("Đã có dữ liệu mẫu. Chạy `python manage.py xoa_du_lieu_mau --xac-nhan` trước.")
    rng = random.Random(hat_giong)
    tai_khoan: list[tuple[str, str, str, str]] = []
    with transaction.atomic():
        khu_vuc = [KhuVuc.objects.get_or_create(ma=ma, defaults={"ten": ten})[0] for ma, ten in KHU_VUC]
        dich_vu = []
        for ma, ten, nhom, loai, gia, dvt in DICH_VU:
            dv, _ = DichVu.objects.get_or_create(
                ma=ma,
                defaults={
                    "ten_dich_vu": ten,
                    "nhom_dich_vu": nhom,
                    "loai_thiet_bi": loai,
                    "don_gia_tham_khao": gia,
                    "don_vi_tinh": dvt,
                    "thoi_han_bao_hanh_ngay": 7 if nhom == VS else 90,
                },
            )
            dich_vu.append(dv)

        van_phong = [(VaiTro.QUAN_TRI, 1), (VaiTro.TONG_DAI, 3), (VaiTro.KE_TOAN, 1), (VaiTro.GIAM_DOC, 1)]
        so = 0
        quan_tri = None
        for vai_tro, so_luong in van_phong:
            for _ in range(so_luong):
                so += 1
                sdt = f"{TIEN_TO_SDT}0000{so:02d}"
                bi_mat = sinh_mat_khau_tam()
                nd = _nguoi_dung(sdt, _ten(rng), vai_tro, bi_mat)
                quan_tri = quan_tri or nd
                tai_khoan.append((nd.get_vai_tro_display(), nd.ho_ten, sdt, bi_mat))

        bay_gio = timezone.now()
        loai_tb = list(HANG)
        for i in range(1, 13):
            sdt = f"{TIEN_TO_SDT}0001{i:02d}"
            pin = sinh_pin()
            nd = _nguoi_dung(sdt, _ten(rng), VaiTro.THO, pin)
            chuyen = rng.sample(loai_tb, k=rng.choice([1, 1, 2, 2, 3]))
            tho = Tho.objects.create(
                nguoi_dung=nd,
                ho_ten=nd.ho_ten,
                so_dien_thoai=sdt,
                hinh_thuc=Tho.HinhThuc.CHINH_THUC if i <= 5 else Tho.HinhThuc.CONG_TAC_VIEN,
                nghi_den=bay_gio + timedelta(days=3) if i in (11, 12) else None,  # 2 thợ đang nghỉ
                kenh_thong_bao=Tho.KenhThongBao.TELEGRAM if i % 9 == 0 else Tho.KenhThongBao.WEB_PUSH,
            )
            tho.ky_nang.set([dv for dv in dich_vu if dv.loai_thiet_bi in chuyen])
            tho.khu_vuc_phu_trach.set(rng.sample(khu_vuc, k=rng.choice([2, 3, 4])))
            tai_khoan.append(("Thợ", nd.ho_ten, sdt, pin))

        for i in range(1, 41):
            kh = KhachHang.objects.create(
                ho_ten=_ten(rng),
                so_dien_thoai=f"{TIEN_TO_SDT}002{i:03d}",
                vip_thu_cong=i <= 3,
                ly_do_vip="Giám đốc giới thiệu" if i <= 3 else "",
                loai_khach=KhachHang.LoaiKhach.VIP if i <= 3 else KhachHang.LoaiKhach.THUONG,
            )
            for j in range(rng.choice([1, 1, 1, 2])):
                dc = DiaChi.objects.create(
                    khach_hang=kh,
                    dia_chi_chi_tiet=f"Số {rng.randint(1, 200)} ngõ {rng.randint(1, 150)} {rng.choice(DUONG)}",
                    khu_vuc=rng.choice(khu_vuc),
                    la_mac_dinh=j == 0,
                    ghi_chu_duong_di=rng.choice(["", "", "Gửi xe ở đầu ngõ", "Nhà có chó, gọi trước"]),
                )
                for _ in range(rng.choice([1, 1, 2])):
                    loai = rng.choice(loai_tb)
                    ThietBi.objects.create(
                        dia_chi=dc,
                        loai_thiet_bi=loai,
                        hang_san_xuat=rng.choice(HANG[loai]),
                        vi_tri_lap=rng.choice(VI_TRI),
                    )
        ghi_nhat_ky(
            None,
            "NAP_DU_LIEU_MAU",
            "DanhMuc:mau",
            du_lieu_sau={
                "khu_vuc": len(khu_vuc),
                "dich_vu": len(dich_vu),
                "nguoi_dung": len(tai_khoan),
                "khach": 40,
            },
        )
    return tai_khoan


def xoa_danh_muc() -> dict[str, int]:
    """Xóa danh mục mẫu. Người dùng mẫu đã có nhật ký (chỉ-thêm) thì khóa thay vì xóa (A-33)."""
    ket_qua = {
        "khach_hang": 0,
        "tho": 0,
        "nguoi_dung_xoa": 0,
        "nguoi_dung_khoa": 0,
        "dich_vu": 0,
        "khu_vuc": 0,
    }
    with transaction.atomic():
        ket_qua["khach_hang"] = (
            KhachHang.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT)
            .delete()[1]
            .get("danh_muc.KhachHang", 0)
        )
        ket_qua["tho"] = (
            Tho.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT).delete()[1].get("danh_muc.Tho", 0)
        )
        co_nhat_ky = set(
            NhatKyThaoTac.objects.exclude(nguoi_dung=None).values_list("nguoi_dung_id", flat=True)
        )
        mau = NguoiDung.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT)
        ket_qua["nguoi_dung_khoa"] = mau.filter(pk__in=co_nhat_ky).update(is_active=False)
        ket_qua["nguoi_dung_xoa"] = mau.exclude(pk__in=co_nhat_ky).delete()[1].get("tai_khoan.NguoiDung", 0)
        for mo_hinh, ds_ma, khoa in ((DichVu, DICH_VU, "dich_vu"), (KhuVuc, KHU_VUC, "khu_vuc")):
            for doi_tuong in mo_hinh.objects.filter(ma__in=[d[0] for d in ds_ma]):
                try:
                    with transaction.atomic():
                        doi_tuong.delete()
                    ket_qua[khoa] += 1
                except ProtectedError:
                    pass  # đang được dữ liệu thật dùng → giữ lại
        ghi_nhat_ky(None, "XOA_DU_LIEU_MAU", "DanhMuc:mau", du_lieu_truoc=ket_qua)
    return ket_qua
