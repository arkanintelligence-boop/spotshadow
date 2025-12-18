FROM python:3.9-slim

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para melhor cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da aplicação
COPY . .

# Criar pasta downloads com permissões corretas
RUN mkdir -p downloads && chmod 755 downloads

# Criar pasta templates se não existir
RUN mkdir -p templates

# Expor a porta que a aplicação vai usar
EXPOSE 5000

# Definir variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]