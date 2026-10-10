"""Máy trạng thái DonSuaChua (SPEC 6.1): kiểm thử tham số hóa MỌI dòng T1–T18 ở mức mô hình và MỌI chuyển
không có trong bảng CHUYEN_TRANG_THAI."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.don_sua_chua.models import LY_DO_HET_LUOT_NHAC, DonSuaChua, HangMucSuaChua
from apps.don_sua_chua.trang_thai import (
    CHUYEN_TRANG_THAI,
    DANG_XU_LY,
    DAU,
    ChuyenTrangThaiKhongHopLe,
    SuKien,
    TrangThaiDon,
    tim_chuyen,
)
from apps.he_thong.models import CauHinh
from apps.tiep_nhan_dieu_phoi.models import LichHen
from tests.conftest import DiaChiFactory, ThietBiFactory, ThoFactory, tao_don, tao_lich

pytestmark = pytest.mark.django_db
T = TrangThaiDon
VS, SC = "VE_SINH_BAO_DUONG", "SUA_CHUA_THAY_VAT_TU"
MOI_TRANG_THAI = [DAU, *T.values]


def _hang_muc(don, gia=500_000, so_luong=1):
    return HangMucSuaChua.objects.create(
        don=don, loai="CONG", mo_ta="Công sửa", so_luong=Decimal(so_luong), don_gia_thuc_te=gia
    )


def _trong_db(don) -> str:
    return DonSuaChua.objects.values_list("trang_thai", flat=True).get(pk=don.pk)


# ============================================================== bảng dữ liệu


def test_bang_co_du_18_dong_va_9_trang_thai():
    assert [d.ma for d in CHUYEN_TRANG_THAI] == [f"T{i}" for i in range(1, 19)]
    assert len(T.values) == 9
    assert len({(t, d.su_kien) for d in CHUYEN_TRANG_THAI for t in d.tu}) == sum(
        len(d.tu) for d in CHUYEN_TRANG_THAI
    )


def test_t14_ap_dung_cho_moi_trang_thai_dang_xu_ly():
    t14 = next(d for d in CHUYEN_TRANG_THAI if d.ma == "T14")
    assert (
        t14.tu
        == DANG_XU_LY
        == {
            T.CHO_XAC_NHAN_LICH,
            T.CHO_CU_THO,
            T.DA_CO_THO,
            T.CHO_DUYET_GIA,
            T.DANG_SUA,
        }
    )


@pytest.mark.parametrize("dong", CHUYEN_TRANG_THAI, ids=lambda d: d.ma)
@pytest.mark.parametrize("tu", MOI_TRANG_THAI, ids=lambda t: t or "DAU")
def test_tim_chuyen_moi_cap_trang_thai_su_kien(dong, tu):
    """Mọi cặp (trạng thái, sự kiện): có trong bảng → đúng đích; không có → ChuyenTrangThaiKhongHopLe."""
    if tu in dong.tu:
        assert tim_chuyen(tu, dong.su_kien) is dong
    else:
        with pytest.raises(ChuyenTrangThaiKhongHopLe):
            tim_chuyen(tu, dong.su_kien)


# ============================================================== từng dòng T1–T18 ở mức mô hình


def _t1():
    return tao_don(), T.CHO_XAC_NHAN_LICH


def _t2():
    dc = DiaChiFactory()
    don = tao_don(dia_chi=dc)  # tạo sẵn để lấy dữ liệu khóa ngoại, rồi dựng đơn mới chưa lưu
    moi = DonSuaChua(
        ma_don="HF000000-999",
        khach_hang=dc.khach_hang,
        dia_chi=dc,
        dich_vu_yeu_cau=don.dich_vu_yeu_cau,
        kenh_tiep_nhan="ZALO",
        nguoi_tao=don.nguoi_tao,
    )
    moi.bat_dau_cu_tho()
    return moi, T.CHO_CU_THO


def _t3():
    don = tao_don()
    don.chot_lich(tao_lich(don))
    return don, T.CHO_CU_THO


def _t4():
    don = tao_don()
    assert don.ghi_nhan_nhac_xac_nhan() is True
    assert don.so_lan_nhac_xac_nhan == 1 and don.lan_nhac_cuoi is not None
    return don, T.CHO_XAC_NHAN_LICH


def _t5():
    don = tao_don(so_lan_nhac_xac_nhan=3)
    assert don.ghi_nhan_nhac_xac_nhan() is False
    assert don.ly_do_huy == LY_DO_HET_LUOT_NHAC
    return don, T.DA_HUY


def _t6():
    don = tao_don(T.CHO_CU_THO)
    lich = tao_lich(don)
    don.de_nghi_doi_lich()
    lich.refresh_from_db()
    assert lich.trang_thai == "DA_HUY"
    return don, T.CHO_XAC_NHAN_LICH


def _t7():
    don = tao_don(T.CHO_CU_THO, canh_bao_chua_cu_duoc=True)
    tho = ThoFactory()
    don.giao_cho_tho(SimpleNamespace(tho=tho))
    assert don.tho == tho and not don.canh_bao_chua_cu_duoc
    return don, T.DA_CO_THO


def _t8():
    don = tao_don(T.DA_CO_THO, tho=ThoFactory())
    don.huy_phan_cong_hien_tai("Thợ báo bận")
    assert don.tho is None
    return don, T.CHO_CU_THO


def _t9():
    don = tao_don(T.DA_CO_THO, nhom=SC)
    don.tho_den_noi()
    assert not don.ds_hang_muc.exists()
    return don, T.CHO_DUYET_GIA


def _t10():
    dc = DiaChiFactory()
    don = tao_don(T.DA_CO_THO, nhom=VS, dia_chi=dc)
    don.thiet_bi.set([ThietBiFactory(dia_chi=dc), ThietBiFactory(dia_chi=dc)])
    don.tho_den_noi()
    hm = don.ds_hang_muc.get()
    assert (hm.loai, hm.so_luong, hm.don_gia_thuc_te, hm.dich_vu) == (
        "CONG",
        Decimal(2),
        don.dich_vu_yeu_cau.don_gia_tham_khao,
        don.dich_vu_yeu_cau,
    )
    return don, T.DANG_SUA


def _t11():
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    _hang_muc(don, 500_000)
    assert don.khach_duyet_gia("Chị Hoa") is True
    assert don.bao_gia_tong == 500_000 and don.bao_gia_nguoi_xac_nhan == "Chị Hoa"
    assert don.bao_gia_xac_nhan_luc is not None
    assert all(hm.la_bao_gia for hm in don.ds_hang_muc.all())
    return don, T.DANG_SUA


def _t12():
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    _hang_muc(don, 2_500_000)  # ≥ ngưỡng 2.000.000 (OI-08)
    assert don.khach_duyet_gia("Anh Nam") is False
    assert don.trang_thai == T.CHO_DUYET_GIA and don.cho_tong_dai_xac_nhan_gia
    don.tong_dai_xac_nhan_gia()
    assert not don.cho_tong_dai_xac_nhan_gia and don.bao_gia_tong == 2_500_000
    return don, T.DANG_SUA


def _t13():
    CauHinh.objects.filter(khoa="PHI_KIEM_TRA_KHI_TU_CHOI").update(gia_tri="50000")
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    don.khach_tu_choi_gia("Giá cao")
    phi = don.ds_hang_muc.get(loai="PHI_KHAC")
    assert phi.thanh_tien == 50_000 and don.ly_do_huy == "Giá cao"
    return don, T.DA_HUY


def _t15():
    don = tao_don(T.DANG_SUA)
    _hang_muc(don, 150_000, 2)
    don.hoan_thanh(so_tien=300_000, so_anh=1)
    assert don.tong_tien_phai_thu == 300_000
    return don, T.HOAN_THANH


def _t16(monkeypatch):
    monkeypatch.setattr(DonSuaChua, "con_han_bao_hanh", property(lambda self: True))
    goc = tao_don(T.HOAN_THANH)
    con = tao_don(dia_chi=goc.dia_chi, loai_don="BAO_HANH", don_goc=goc)
    goc.mo_bao_hanh(con)
    return goc, T.DANG_BAO_HANH


def _t17():
    don = tao_don(T.DANG_BAO_HANH)
    don.ket_thuc_bao_hanh()
    return don, T.HOAN_THANH


def _t18():
    don = tao_don(T.HOAN_THANH)
    don.dong()
    return don, T.DA_DONG


CAC_DONG = {
    "T1": _t1,
    "T2": _t2,
    "T3": _t3,
    "T4": _t4,
    "T5": _t5,
    "T6": _t6,
    "T7": _t7,
    "T8": _t8,
    "T9": _t9,
    "T10": _t10,
    "T11": _t11,
    "T12": _t12,
    "T13": _t13,
    "T15": _t15,
    "T16": _t16,
    "T17": _t17,
    "T18": _t18,
}


def test_moi_dong_bang_deu_co_kiem_thu():
    assert set(CAC_DONG) | {"T14"} == {d.ma for d in CHUYEN_TRANG_THAI}


@pytest.mark.parametrize("ma", list(CAC_DONG))
def test_chuyen_trang_thai_tung_dong(ma, monkeypatch):
    ham = CAC_DONG[ma]
    don, den = ham(monkeypatch) if ma == "T16" else ham()
    assert don.trang_thai == den
    assert _trong_db(don) == den  # đã lưu
    assert don._chuyen_gan_nhat[0] == ma  # đúng dòng của bảng


@pytest.mark.parametrize("tu", sorted(DANG_XU_LY))
def test_t14_khach_huy_tu_moi_trang_thai_dang_xu_ly(tu):
    don = tao_don(tu)
    lich = tao_lich(don)
    don.huy("Khách đổi ý", nguoi=None)
    lich.refresh_from_db()
    assert _trong_db(don) == T.DA_HUY and don.ly_do_huy == "Khách đổi ý"
    assert lich.trang_thai == "DA_HUY"
    assert don._chuyen_gan_nhat[0] == "T14"


# ============================================================== chuyển KHÔNG có trong bảng (mức phương thức)

PHUONG_THUC = {
    "chot_lich": (SuKien.CHOT_LICH, lambda d: d.chot_lich(tao_lich(d))),
    "ghi_nhan_nhac_xac_nhan": (SuKien.NHAC_XAC_NHAN, lambda d: d.ghi_nhan_nhac_xac_nhan()),
    "de_nghi_doi_lich": (SuKien.DE_NGHI_DOI_LICH, lambda d: d.de_nghi_doi_lich()),
    "giao_cho_tho": (SuKien.THO_NHAN_VIEC, lambda d: d.giao_cho_tho(SimpleNamespace(tho=ThoFactory()))),
    "huy_phan_cong_hien_tai": (SuKien.RUT_VIEC, lambda d: d.huy_phan_cong_hien_tai("bận")),
    "tho_den_noi": (SuKien.DEN_NOI_VE_SINH, lambda d: d.tho_den_noi()),
    "khach_duyet_gia": (SuKien.KHACH_DUYET_GIA, lambda d: d.khach_duyet_gia("A")),
    "tong_dai_xac_nhan_gia": (SuKien.TONG_DAI_XAC_NHAN_GIA, lambda d: d.tong_dai_xac_nhan_gia()),
    "khach_tu_choi_gia": (SuKien.KHACH_TU_CHOI_GIA, lambda d: d.khach_tu_choi_gia("x")),
    "huy": (SuKien.KHACH_HUY, lambda d: d.huy("x")),
    "hoan_thanh": (SuKien.HOAN_THANH, lambda d: d.hoan_thanh(100_000, 5)),
    "mo_bao_hanh": (
        SuKien.MO_BAO_HANH,
        lambda d: d.mo_bao_hanh(tao_don(dia_chi=d.dia_chi, loai_don="BAO_HANH", don_goc=d)),
    ),
    "ket_thuc_bao_hanh": (SuKien.KET_THUC_BAO_HANH, lambda d: d.ket_thuc_bao_hanh()),
    "dong": (SuKien.HET_HAN_BAO_HANH, lambda d: d.dong()),
}

TRUONG_HOP_SAI = [
    (ten, tt)
    for ten, (su_kien, _) in PHUONG_THUC.items()
    for tt in T.values
    if tt not in next(d for d in CHUYEN_TRANG_THAI if d.su_kien == su_kien).tu
]


@pytest.mark.parametrize(("ten", "trang_thai"), TRUONG_HOP_SAI, ids=[f"{a}-{b}" for a, b in TRUONG_HOP_SAI])
def test_phuong_thuc_nghiep_vu_tu_choi_trang_thai_nguon_sai(ten, trang_thai, monkeypatch):
    monkeypatch.setattr(DonSuaChua, "con_han_bao_hanh", property(lambda self: True))
    don = tao_don(trang_thai, nhom=SC, tho=ThoFactory() if trang_thai != T.CHO_CU_THO else None)
    _hang_muc(don)
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        PHUONG_THUC[ten][1](don)
    assert _trong_db(don) == trang_thai


# ============================================================== điều kiện trong bảng


def test_t7_don_da_co_tho_khong_nhan_them(tao_nguoi_dung):
    don = tao_don(T.CHO_CU_THO, tho=ThoFactory())
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="đã có thợ"):
        don.giao_cho_tho(SimpleNamespace(tho=ThoFactory()))


def test_t15_thieu_anh_khong_hoan_thanh_duoc():
    don = tao_don(T.DANG_SUA)
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="ảnh"):
        don.hoan_thanh(100_000, so_anh=0)
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        don.hoan_thanh(None, so_anh=1)
    assert _trong_db(don) == T.DANG_SUA


def test_t16_phieu_het_han_khong_mo_bao_hanh():
    goc = tao_don(T.HOAN_THANH)  # chưa có phiếu bảo hành → coi như hết hạn
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="hết hạn"):
        goc.mo_bao_hanh(tao_don(dia_chi=goc.dia_chi, loai_don="BAO_HANH", don_goc=goc))


def test_t18_phieu_con_han_khong_dong(monkeypatch):
    monkeypatch.setattr(DonSuaChua, "con_han_bao_hanh", property(lambda self: True))
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="còn hạn"):
        tao_don(T.HOAN_THANH).dong()


def test_br06_khach_duyet_gia_tren_don_ve_sinh_bi_loi():
    don = tao_don(T.CHO_DUYET_GIA, nhom=VS)
    _hang_muc(don)
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="BR06"):
        don.khach_duyet_gia("A")


def test_br06_bao_gia_vuot_nguong_can_t12():
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    _hang_muc(don, 2_000_000)
    assert don.khach_duyet_gia("A") is False
    assert _trong_db(don) == T.CHO_DUYET_GIA and don.cho_tong_dai_xac_nhan_gia
    assert don.khach_duyet_gia("A") is False  # khách đồng ý lại vẫn phải chờ tổng đài


def test_br06_nguong_bang_0_la_tat():
    CauHinh.objects.filter(khoa="NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN").update(gia_tri="0")
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    _hang_muc(don, 9_000_000)
    assert don.khach_duyet_gia("A") is True


def test_br06_chua_co_bao_gia_khong_duyet():
    don = tao_don(T.CHO_DUYET_GIA, nhom=SC)
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="hạng mục"):
        don.khach_duyet_gia("A")


def test_br05_don_bao_hanh_dong_cong_khong_thu_khach():
    goc = tao_don(T.HOAN_THANH)
    con = tao_don(
        T.DA_CO_THO, dia_chi=goc.dia_chi, loai_don="BAO_HANH", don_goc=goc, nguyen_nhan_bao_hanh="TAY_NGHE"
    )
    con.tho_den_noi()
    assert con.ds_hang_muc.get().ben_chiu_chi_phi == "THO"


# ============================================================== chỉ đổi trạng thái qua phương thức nghiệp vụ


def test_khong_gan_truc_tiep_trang_thai():
    don = tao_don()
    don.trang_thai = T.HOAN_THANH
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="phương thức nghiệp vụ"):
        don.save()
    assert _trong_db(don) == T.CHO_XAC_NHAN_LICH


def test_khong_tao_don_bo_qua_khoi_tao(tao_nguoi_dung):
    dc = DiaChiFactory()
    don = tao_don(dia_chi=dc)
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        DonSuaChua.objects.create(
            ma_don="HF000000-998",
            khach_hang=dc.khach_hang,
            dia_chi=dc,
            dich_vu_yeu_cau=don.dich_vu_yeu_cau,
            kenh_tiep_nhan="ZALO",
            nguoi_tao=don.nguoi_tao,
            trang_thai=T.HOAN_THANH,
        )


def test_luu_truong_khac_khong_bi_chan():
    don = tao_don()
    don.mo_ta_su_co = "Sửa mô tả"
    don.save()
    don.refresh_from_db()
    assert don.mo_ta_su_co == "Sửa mô tả"


def test_lich_hen_huy_khi_doi_lich_t6_chi_lich_hieu_luc():
    don = tao_don(T.CHO_CU_THO)
    cu = tao_lich(don, trang_thai="DA_THAY_THE")
    tao_lich(don)
    don.de_nghi_doi_lich()
    assert set(LichHen.objects.filter(don=don).values_list("trang_thai", flat=True)) == {
        "DA_THAY_THE",
        "DA_HUY",
    }
    cu.refresh_from_db()
    assert cu.trang_thai == "DA_THAY_THE"


def test_thanh_tien_lam_tron_den_dong():
    don = tao_don()
    hm = HangMucSuaChua(
        don=don, loai="VAT_TU", mo_ta="Ống đồng", so_luong=Decimal("1.5"), don_gia_thuc_te=33_333
    )
    assert hm.thanh_tien == 50_000  # 49.999,5 → 50.000
