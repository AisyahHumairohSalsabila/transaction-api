# ---------- Stage 1: builder ----------
# Install dependency ke folder terpisah supaya image akhir bersih.
FROM python:3.12-alpine AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# User non-root: kalau aplikasi dibobol, penyerang tidak punya hak root.
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app

USER app
EXPOSE 8000

# Tidak ada kredensial di sini. DATABASE_URL disuntik saat container dijalankan.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
