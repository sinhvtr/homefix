"""BR03 — một đơn một thợ; nhiều thợ cùng nhận → người bấm trước. Hai luồng song song thật trên PostgreSQL."""

import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import connection

from apps.don_sua_chua.models import DonSuaChua
from apps.tai_khoan.models import VaiTro
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong
from tests.conftest import DichVuFactory, NguoiDungFactory, don_cho_cu_tho, tao_tho_phu_hop

HEN = datetime(2099, 6, 1, 8, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
@pytest.mark.parametrize("so_tho", [2, 5])
def test_br03_nhieu_tho_bam_nhan_cung_luc_chi_mot_nguoi_duoc(so_tho):
    tong_dai = NguoiDungFactory(vai_tro=VaiTro.TONG_DAI)
    dv = DichVuFactory()
    don = don_cho_cu_tho(ngay_gio=HEN, dich_vu=dv)
    ds_tho = [tao_tho_phu_hop(dv) for _ in range(so_tho)]
    PhanCongDAO.gui_de_nghi(tong_dai, don, [t.pk for t in ds_tho])
    pc_theo_tho = {pc.tho_id: pc.pk for pc in PhanCong.objects.filter(don=don)}

    rao = threading.Barrier(so_tho)
    ket_qua, loi = {}, []

    def bam_nhan(tho):
        try:
            rao.wait(timeout=10)
            ket_qua[tho.pk] = PhanCongDAO.nhan_viec(tho.nguoi_dung, pc_theo_tho[tho.pk])
        except Exception as e:  # pragma: no cover — để kiểm thử báo lỗi rõ
            loi.append(e)
        finally:
            connection.close()

    luong = [threading.Thread(target=bam_nhan, args=(t,)) for t in ds_tho]
    for lu in luong:
        lu.start()
    for lu in luong:
        lu.join(timeout=30)

    assert not loi, loi
    thang = [tho_id for tho_id, (ok, _) in ket_qua.items() if ok]
    assert len(thang) == 1
    assert all(tm == "Đơn đã có thợ nhận" for ok, tm in ket_qua.values() if not ok)
    assert PhanCong.objects.filter(don=don, trang_thai="DA_NHAN").count() == 1
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (d.trang_thai, d.tho_id) == ("DA_CO_THO", thang[0])
    assert PhanCong.objects.filter(don=don, trang_thai="DA_HUY").count() == so_tho - 1
