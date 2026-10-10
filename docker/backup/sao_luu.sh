#!/bin/sh
# Sao lưu CSDL (SPEC 12): pg_dump -Fc → /backups/homefix_YYYYmmdd.dump, xóa bản cũ hơn BACKUP_KEEP_DAYS ngày.
set -eu
TEP="/backups/homefix_$(date +%Y%m%d).dump"
pg_dump -Fc -f "$TEP.tmp"
mv "$TEP.tmp" "$TEP"
find /backups -name 'homefix_*.dump' -type f -mtime +"${BACKUP_KEEP_DAYS:-14}" -delete
echo "Đã sao lưu: $TEP"
