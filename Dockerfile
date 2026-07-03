# Dockerfile para Hugging Face Spaces
# Flask app COREGOV - migração Render → HF Spaces
# Usa Python 3.14 (compatível com o render.yaml atual)

FROM python:3.14-slim-bookworm

# =========================
# CONFIGURAÇÕES DO SISTEMA
# =========================
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=7860

# =========================
# DEPENDÊNCIAS DO SISTEMA
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# COPIAR REQUIREMENTS
# =========================
COPY requirements-hf.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-hf.txt

# =========================
# COPIAR O APP
# =========================
COPY . .

# =========================
# CRIAR DIRETÓRIOS PERSISTENTES
# HF Spaces: /data persiste entre deploys
# =========================
RUN mkdir -p /data/uploads \
    /data/db \
    /data/storage \
    /tmp/coregov-uploads

# =========================
# SCRIPT DE INÍCIO
# =========================
RUN echo '#!/bin/bash\n\
# Se o banco SQLite não existir, criar com schema inicial\n\
if [ ! -f /data/db/coregov.db ]; then\n\
    echo "📦 Criando banco SQLite pela primeira vez..."\n\
    python /app/dashboard/migrar_sqlite.py\n\
    echo "✅ Banco criado!"\n\
fi\n\
\n\
# Iniciar o servidor\n\
echo "🚀 Iniciando COREGOV App no Hugging Face Spaces..."\n\
gunicorn --timeout 300 --workers 2 --max-requests 1000 \
    --worker-class sync \
    --bind 0.0.0.0:$PORT \
    app_sqlite:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# =========================
# HEALTHCHECK
# =========================
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# =========================
# PORTA PADRÃO HF SPACES
# =========================
EXPOSE 7860

# =========================
# COMANDO DE INÍCIO
# =========================
CMD ["/app/start.sh"]
