FROM python:3.9-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da aplicação
COPY . .

# Criar pastas necessárias
RUN mkdir -p downloads

# Verificar se arquivos essenciais existem
RUN ls -la templates/ || echo "Templates directory missing"
RUN ls -la favicon.png || echo "Favicon missing"
RUN ls -la logotipo-semfundo.png || echo "Logo missing"

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV HOST=0.0.0.0

# Expor porta
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando de inicialização mais robusto
CMD ["python", "-u", "app.py"]