"""DichVuThongBao (SPEC 11): luôn tạo bản ghi ThongBao (chuông trong ứng dụng) trong giao dịch hiện tại,
rồi SAU KHI COMMIT xếp tác vụ nền gửi qua kênh của người nhận — không gọi mạng trong giao dịch."""

import logging
from functools import partial

from django.conf import settings
from django.db import transaction

from .models import ThongBao

log = logging.getLogger(__name__)


class DichVuThongBao:
    @staticmethod
    def gui(nguoi_nhan, tieu_de: str, noi_dung: str = "", duong_dan: str = "") -> ThongBao:
        tb = ThongBao.objects.create(
            nguoi_nhan=nguoi_nhan, tieu_de=tieu_de[:200], noi_dung=noi_dung, duong_dan=duong_dan
        )
        transaction.on_commit(partial(_xep_hang_gui, tb.pk))
        return tb


def _xep_hang_gui(thong_bao_id: int) -> None:
    if settings.THONG_BAO_DONG_BO:
        from .tac_vu import gui_qua_kenh

        gui_qua_kenh(thong_bao_id)
        return
    from django_q.tasks import async_task

    async_task("apps.thong_bao.tac_vu.gui_qua_kenh", thong_bao_id, task_name=f"thong_bao_{thong_bao_id}")
