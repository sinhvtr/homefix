# Lệnh vận hành HomeFix (SPEC 15-P0). Mặc định chạy trong Docker (Python 3.12 + PostgreSQL 16).
# Chạy trực tiếp trên máy (đã kích hoạt venv, CSDL dev ở 127.0.0.1:5433): make check RUN=
DC ?= docker compose
RUN ?= $(DC) run --rm --no-deps web

.PHONY: up down build logs migrate test check fmt vapid seed backup thu-khoi-phuc anh-xa-bang quan-tri

up:
	$(DC) up -d --build

down:
	$(DC) down

build:
	$(DC) build

logs:
	$(DC) logs -f --tail=100

migrate:
	$(RUN) python manage.py migrate

test:
	$(DC) up -d --wait db
	$(RUN) pytest

check:
	$(DC) up -d --wait db
	$(RUN) sh -c "ruff check . && ruff format --check . && lint-imports && python manage.py check && python manage.py makemigrations --check --dry-run && pytest"

fmt:
	$(RUN) sh -c "ruff check --fix . && ruff format ."

vapid:
	$(RUN) python manage.py tao_khoa_vapid

seed:
	$(RUN) python manage.py nap_du_lieu_mau

backup:
	$(DC) exec backup sh /usr/local/bin/sao_luu.sh

# Nạp bản sao lưu mới nhất vào CSDL tạm, so số dòng, xóa CSDL tạm (không động vào CSDL thật)
thu-khoi-phuc:
	$(DC) exec backup sh /usr/local/bin/thu_khoi_phuc.sh

anh-xa-bang:
	$(RUN) python manage.py sinh_anh_xa_bang

quan-tri:
	$(DC) exec web python manage.py tao_quan_tri
