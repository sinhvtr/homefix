FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TAILWIND_CLI_PATH=/opt/tailwind

WORKDIR /app

# Cài phụ thuộc trước để tận dụng cache của Docker. CAI_DEV=1 cài thêm công cụ kiểm thử (dùng ở máy dev).
ARG CAI_DEV=0
COPY pyproject.toml ./
RUN if [ "$CAI_DEV" = "1" ]; then pip install ".[dev]"; else pip install .; fi

COPY . .

# Tải Tailwind CLI (bản độc lập, không cần Node) và build CSS lúc đóng gói.
RUN mkdir -p /opt/tailwind \
    && DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py tailwind build \
    && useradd --create-home --uid 1000 homefix \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R homefix:homefix /app /opt/tailwind

USER homefix

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/suc-khoe/', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi -w 3 --threads 2 -b 0.0.0.0:8000 --access-logfile -"]
