#!/bin/sh
# Thử khôi phục (SPEC 10 — sao lưu): nạp bản sao lưu mới nhất vào CSDL tạm, so số dòng các bảng chính với CSDL đang
# chạy, rồi xóa CSDL tạm. Không động vào CSDL thật. Chạy: make thu-khoi-phuc
set -eu
TEP="${1:-$(ls -1t /backups/homefix_*.dump 2>/dev/null | head -n1)}"
[ -n "$TEP" ] && [ -f "$TEP" ] || { echo "Không có bản sao lưu trong /backups"; exit 1; }
TAM="homefix_thu_khoi_phuc"
dropdb --if-exists "$TAM"
createdb "$TAM"
trap 'dropdb --if-exists "$TAM"' EXIT
pg_restore --no-owner --exit-on-error -d "$TAM" "$TEP"
LOI=0
for BANG in tblDonSuaChua tblThanhToan tblPhieuDoiSoat tblNhatKy tblKhachHang tblNhanVien; do
  GOC=$(psql -tAc "SELECT count(*) FROM \"$BANG\"")
  KP=$(psql -d "$TAM" -tAc "SELECT count(*) FROM \"$BANG\"")
  echo "$BANG: đang chạy $GOC dòng · bản khôi phục $KP dòng"
  [ "$GOC" -ge "$KP" ] || LOI=1
  [ "$KP" -gt 0 ] || [ "$GOC" -eq 0 ] || LOI=1
done
[ "$LOI" -eq 0 ] && echo "Khôi phục thử thành công từ $TEP" || { echo "Bản khôi phục thiếu dữ liệu"; exit 1; }
