"""P6 — trang nhật ký (NFR06), IP người thao tác, sinh_anh_xa_bang, rà soát bảo mật prod (check --deploy)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from apps.he_thong.models import NhatKyThaoTac
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.models import VaiTro
from tests.conftest import NguoiDungFactory

pytestmark = pytest.mark.django_db


# ============================================================== trang nhật ký


@pytest.fixture
def nhat_ky_mau():
    a, b = NguoiDungFactory(ho_ten="Tổng đài A"), NguoiDungFactory(ho_ten="Tổng đài B")
    for i in range(60):
        ghi_nhat_ky(a, "TAO_DON", f"DonSuaChua:HF260901-{i:03d}", du_lieu_sau={"i": i})
    ghi_nhat_ky(b, "SUA_GIA", "DichVu:VS-DH-TT", {"don_gia": 150_000}, {"don_gia": 170_000})
    ghi_nhat_ky(None, "NHAC_XAC_NHAN", "DonSuaChua:HF260901-007")
    return a, b


def test_nhat_ky_loc_va_phan_trang(client, nhat_ky_mau):
    a, b = nhat_ky_mau
    client.force_login(NguoiDungFactory(vai_tro=VaiTro.QUAN_TRI))
    trang = client.get("/quan-tri/nhat-ky/").content.decode()
    assert "62 dòng" in trang and "trang 1/2" in trang and "Trang sau" in trang
    assert "62 dòng" not in client.get("/quan-tri/nhat-ky/", {"hanh_dong": "SUA_GIA"}).content.decode()
    sua_gia = client.get("/quan-tri/nhat-ky/", {"hanh_dong": "SUA_GIA"}).content.decode()
    assert "1 dòng" in sua_gia and "170000" in sua_gia and "Tổng đài B" in sua_gia
    assert "1 dòng" in client.get("/quan-tri/nhat-ky/", {"nguoi": "he_thong"}).content.decode()
    assert "2 dòng" in client.get("/quan-tri/nhat-ky/", {"doi_tuong": "HF260901-007"}).content.decode()
    assert "60 dòng" in client.get("/quan-tri/nhat-ky/", {"nguoi": a.pk}).content.decode()
    trang2 = client.get("/quan-tri/nhat-ky/", {"hanh_dong": "TAO_DON", "trang": 2}).content.decode()
    assert "trang 2/2" in trang2 and "?hanh_dong=TAO_DON&trang=1" in trang2  # giữ bộ lọc khi chuyển trang
    # tham số rác không làm lỗi
    assert client.get("/quan-tri/nhat-ky/", {"nguoi": "x'or", "tu": "ab", "trang": "z"}).status_code == 200


def test_nhat_ky_chi_quan_tri_giam_doc(client, nhat_ky_mau):
    client.force_login(NguoiDungFactory(vai_tro=VaiTro.GIAM_DOC))
    assert client.get("/quan-tri/nhat-ky/").status_code == 200
    for vai_tro in (VaiTro.TONG_DAI, VaiTro.KE_TOAN):
        client.force_login(NguoiDungFactory(vai_tro=vai_tro))
        assert client.get("/quan-tri/nhat-ky/").status_code == 403


def test_nhat_ky_ghi_ip_nguoi_thao_tac(client):
    td = NguoiDungFactory(vai_tro=VaiTro.TONG_DAI)
    client.force_login(td)
    client.post(
        "/danh-muc/khach-hang/moi/",
        {"so_dien_thoai": "0912000111", "ho_ten": "Khách IP"},
        REMOTE_ADDR="10.1.2.3",
    )
    nk = NhatKyThaoTac.objects.filter(nguoi_dung=td).latest("thoi_diem")
    assert nk.dia_chi_ip == "10.1.2.3"
    client.post(
        "/danh-muc/khach-hang/moi/",
        {"so_dien_thoai": "0912000222", "ho_ten": "Qua tunnel"},
        HTTP_X_FORWARDED_FOR="203.0.113.9, 127.0.0.1",
    )
    assert NhatKyThaoTac.objects.filter(nguoi_dung=td).latest("thoi_diem").dia_chi_ip == "203.0.113.9"
    assert ghi_nhat_ky(None, "TAC_VU", "X:1").dia_chi_ip is None  # ngoài yêu cầu (tác vụ nền)


# ============================================================== sinh_anh_xa_bang


def test_sinh_anh_xa_bang_du_lop_bang_cot(tmp_path):
    tep = tmp_path / "anh_xa.md"
    call_command("sinh_anh_xa_bang", "--tep", str(tep))
    nd = tep.read_text(encoding="utf-8")
    for bang in (
        "tblNhanVien",
        "tblKhuVuc",
        "tblKhachHang",
        "tblDiaChi",
        "tblThietBi",
        "tblDichVu",
        "tblTho",
        "tblDonSuaChua",
        "tblHangMucSuaChua",
        "tblLichHen",
        "tblPhanCong",
        "tblThanhToan",
        "tblPhieuDoiSoat",
        "tblPhieuBaoHanh",
        "tblNhatKy",
        "tblThongBao",
        "tblDangKyPush",
        "tblCauHinh",
        "tblBoDemMaDon",
    ):
        assert f"→ `{bang}`" in nd, bang
    assert "| `ma_don` | `ma_don` | CharField | varchar(16) |  | UNIQUE | mã đơn |" in nd
    assert "FK → tblDonSuaChua (DonSuaChua), PROTECT" in nd
    assert "`mot_phan_cong_da_nhan_moi_don`: UNIQUE (don) WHERE" in nd
    # tất định: sinh lại giống hệt
    call_command("sinh_anh_xa_bang", "--tep", str(tmp_path / "lan2.md"))
    assert (tmp_path / "lan2.md").read_text(encoding="utf-8") == nd


def test_docs_anh_xa_bang_khop_mo_hinh_hien_tai():
    """Quên chạy `make anh-xa-bang` sau khi đổi mô hình → kiểm thử đỏ."""
    call_command("sinh_anh_xa_bang", "--kiem-tra")


def test_sinh_anh_xa_bang_kiem_tra_bao_loi_khi_cu(tmp_path):
    tep = tmp_path / "cu.md"
    tep.write_text("# cũ\n", encoding="utf-8")
    with pytest.raises(CommandError, match="đã cũ"):
        call_command("sinh_anh_xa_bang", "--tep", str(tep), "--kiem-tra")


# ============================================================== rà soát bảo mật prod


def test_check_deploy_cau_hinh_prod_sach():
    """`manage.py check --deploy` với config.settings.prod: không còn cảnh báo (A-90)."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": "khoa-thu-dai-ngau-nhien-" + "Ab9xZ" * 10,
        "DJANGO_ALLOWED_HOSTS": "homefix.vi-du.ts.net",
        "DJANGO_COOKIE_SECURE": "1",
        "DJANGO_DEBUG": "1",  # prod.py luôn ép DEBUG = False
    }
    kq = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=Path(settings.BASE_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert kq.returncode == 0, kq.stdout + kq.stderr
    assert "no issues" in kq.stdout


# ============================================================== /huong-dan/ (NFR09)


def test_markdown_don_gian_escape_va_dinh_dang():
    from apps.he_thong.markdown_don_gian import neo, sang_html

    html, muc_luc = sang_html(
        "# Bỏ\n\n## Tổng đài\n\nĐoạn **đậm** `n` <script>x</script>\n\n1. Một\n   nối tiếp\n2. Hai\n- Ba\n"
    )
    assert muc_luc == [("tong-dai", "Tổng đài")]
    assert '<h2 id="tong-dai"' in html and "Bỏ" not in html
    assert (
        "<strong>đậm</strong>" in html
        and "<code" in html
        and "&lt;script&gt;" in html
        and "<script>" not in html
    )
    assert "<li>Một nối tiếp</li><li>Hai</li></ol>" in html and "<ul" in html
    assert neo("Quản trị (tổ trưởng tổng đài)") == "quan-tri-to-truong-tong-dai"


@pytest.mark.parametrize(
    ("vai_tro", "phan"),
    [
        (VaiTro.TONG_DAI, "tong-dai"),
        (VaiTro.KE_TOAN, "ke-toan"),
        (VaiTro.GIAM_DOC, "giam-doc"),
        (VaiTro.QUAN_TRI, "quan-tri-to-truong-tong-dai"),
    ],
)
def test_huong_dan_theo_vai_tro(client_vai_tro, vai_tro, phan):
    trang = client_vai_tro(vai_tro).get("/huong-dan/").content.decode()
    assert (
        f'href="#{phan}" class="inline-flex min-h-11 items-center rounded border px-3 border-sky-700' in trang
    )
    assert 'href="/huong-dan/"' in trang  # có trong menu


def test_huong_dan_cho_tho_va_can_dang_nhap(client, client_vai_tro):
    assert client.get("/huong-dan/").status_code == 302
    c = client_vai_tro(VaiTro.THO)
    assert 'id="tho-dien-thoai"' in c.get("/huong-dan/").content.decode()
    assert 'href="/huong-dan/"' in c.get("/tho/cai-dat/").content.decode()


def test_lenh_quan_tri_chay_duoc_khi_chua_co_csdl():
    """Build image (Dockerfile chạy `manage.py tailwind build`) không có CSDL: import URL/form không được truy vấn
    CSDL (A-94 — trước đây ô chọn dịch vụ ở form tiếp nhận truy vấn ngay lúc khai báo lớp)."""
    env = {**os.environ, "DATABASE_URL": "postgres://khong:co@127.0.0.1:1/khong_co"}
    kq = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=Path(settings.BASE_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert kq.returncode == 0, kq.stdout + kq.stderr


def test_tep_tinh_khong_tro_toi_source_map_thieu():
    """CompressedManifestStaticFilesStorage (prod) dừng collectstatic nếu JS/CSS trỏ tới .map không có (A-94)."""
    import re

    for tep in (Path(settings.BASE_DIR) / "static").rglob("*.*s"):
        if tep.suffix not in (".js", ".css"):
            continue
        for ten in re.findall(
            r"sourceMappingURL=([^\s*]+)", tep.read_text(encoding="utf-8", errors="ignore")
        ):
            assert (tep.parent / ten).exists(), f"{tep.name} trỏ tới {ten} không tồn tại"
