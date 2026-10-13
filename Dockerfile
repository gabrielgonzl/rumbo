FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATRIMONIO_ESCUCHA=0.0.0.0 \
    PATRIMONIO_NO_ABRIR=1 \
    PATRIMONIO_DATOS=/data

WORKDIR /srv/rumbo

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY demo ./demo

# Usuario sin privilegios; /data es donde viven tus datos (se monta desde el anfitrión).
RUN useradd --system --uid 10001 --no-create-home rumbo \
 && mkdir /data && chown rumbo /data
USER rumbo
VOLUME /data
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if b'patrimonio' in urllib.request.urlopen('http://127.0.0.1:8765/api/ping', timeout=3).read() else 1)"

CMD ["python", "-m", "app"]
