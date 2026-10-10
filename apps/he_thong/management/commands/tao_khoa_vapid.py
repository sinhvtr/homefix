import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64(du_lieu: bytes) -> str:
    return base64.urlsafe_b64encode(du_lieu).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "In cặp khóa VAPID cho Web Push để chép vào .env (SPEC 8.1)."

    def handle(self, *args, **options):
        khoa_rieng = ec.generate_private_key(ec.SECP256R1())
        rieng = khoa_rieng.private_numbers().private_value.to_bytes(32, "big")
        cong_khai = khoa_rieng.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write("# Chép hai dòng sau vào .env — không commit khóa riêng.")
        self.stdout.write(f"VAPID_PUBLIC_KEY={_b64(cong_khai)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={_b64(rieng)}")
