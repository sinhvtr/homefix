import time

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.thong_bao.telegram import xu_ly_cap_nhat


class Command(BaseCommand):
    help = "Nhận lệnh /start từ bot Telegram bằng long polling (thay cho webhook khi không có URL công khai)."

    def add_arguments(self, parser):
        parser.add_argument("--mot-lan", action="store_true", help="Lấy một lượt cập nhật rồi thoát.")

    def handle(self, *args, mot_lan=False, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("Chưa cấu hình TELEGRAM_BOT_TOKEN.")
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
        offset = None
        while True:
            try:
                phan_hoi = httpx.get(url, params={"timeout": 50, "offset": offset}, timeout=60).json()
            except (httpx.HTTPError, ValueError) as loi:
                self.stderr.write(f"Lỗi Telegram: {loi}")
                time.sleep(5)
                continue
            for cap_nhat in phan_hoi.get("result", []):
                offset = cap_nhat["update_id"] + 1
                if xu_ly_cap_nhat(cap_nhat):
                    self.stdout.write("Đã gắn một tài khoản Telegram.")
            if mot_lan:
                return
