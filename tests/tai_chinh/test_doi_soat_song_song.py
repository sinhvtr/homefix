"""UC12 — hai kế toán cùng lập phiếu cho một thợ cùng lúc: mỗi ThanhToan chỉ vào đúng một phiếu (PostgreSQL thật)."""

import threading

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.tai_chinh.dao import DoiSoatDAO
from apps.tai_chinh.models import PhieuDoiSoat, ThanhToan
from apps.tai_khoan.models import VaiTro
from tests.conftest import NguoiDungFactory, don_hoan_thanh


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_uc12_lap_phieu_song_song_khong_trung_thanh_toan():
    _, tho, _ = don_hoan_thanh(so_tien=150_000)
    don_hoan_thanh(so_tien=150_000, tho=tho)
    ds_ke_toan = [NguoiDungFactory(vai_tro=VaiTro.KE_TOAN) for _ in range(3)]
    rao = threading.Barrier(len(ds_ke_toan))
    ket_qua, loi = [], []

    def lap(kt):
        try:
            rao.wait(timeout=10)
            ket_qua.append(DoiSoatDAO.lap_phieu(kt, tho).pk)
        except ValidationError as e:
            ket_qua.append(str(e))
        except Exception as e:  # pragma: no cover — để kiểm thử báo lỗi rõ
            loi.append(e)
        finally:
            connection.close()

    luong = [threading.Thread(target=lap, args=(kt,)) for kt in ds_ke_toan]
    for lu in luong:
        lu.start()
    for lu in luong:
        lu.join(timeout=30)

    assert not loi, loi
    assert PhieuDoiSoat.objects.count() == 1
    assert sum(isinstance(k, int) for k in ket_qua) == 1
    p = PhieuDoiSoat.objects.get()
    assert set(ThanhToan.objects.values_list("phieu_doi_soat_id", flat=True)) == {p.pk}
    assert p.tong_tien_thu == 300_000
