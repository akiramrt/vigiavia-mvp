# syntax=docker/dockerfile:1.7
# VigiaVia MVP — imagem enxuta (sem PyTorch), multi-stage, usuário não root, sem segredos.
# Segredos (ex.: METRICS_TOKEN) entram SÓ em tempo de execução, como variável de ambiente.

FROM python:3.12-slim-bookworm AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/instalado -r requirements.txt

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="vigiavia-mvp" \
      org.opencontainers.image.source="https://github.com/akiramrt/vigiavia-mvp" \
      org.opencontainers.image.licenses="AGPL-3.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    VIGIAVIA_DB=/dados/vigiavia.db VIGIAVIA_THREADS=2
# atualiza pacotes do SO (correções de segurança) e cria o usuário sem privilégios
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin vigia \
    && mkdir /dados && chown vigia:vigia /dados
COPY --from=dependencias /instalado /usr/local
WORKDIR /app
COPY src/ src/
COPY api/ api/
COPY configs/ configs/
COPY modelos/vigiavia_buracos.onnx modelos/
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
