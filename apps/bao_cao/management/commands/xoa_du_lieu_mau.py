from django.core.management.base import BaseCommand, CommandError

from apps.bao_cao.du_lieu_mau import xoa_du_lieu_mau


class Command(BaseCommand):
    help = "Xóa dữ liệu mẫu trước khi chạy thật (SPEC 14.4)."

    def add_arguments(self, parser):
        parser.add_argument("--xac-nhan", action="store_true", help="Bắt buộc, để tránh chạy nhầm.")

    def handle(self, *args, xac_nhan=False, **options):
        if not xac_nhan:
            raise CommandError("Thêm --xac-nhan để xóa dữ liệu mẫu.")
        ket_qua = xoa_du_lieu_mau()
        self.stdout.write(self.style.SUCCESS(f"Đã xóa dữ liệu mẫu: {ket_qua}"))
