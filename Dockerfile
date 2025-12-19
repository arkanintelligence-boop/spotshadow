FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn para produção
RUN pip install gunicorn

# Copiar todo o código da aplicação
COPY . .

# Criar pastas necessárias com permissões corretas
RUN mkdir -p downloads templates && \
    chmod 777 downloads

# Testar se SpotDL funciona
RUN spotdl --version

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV HOST=0.0.0.0

# Expor porta
EXPOSE 5000

# Comando de inicialização com gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "app:app"]