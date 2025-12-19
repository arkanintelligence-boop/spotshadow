#!/bin/bash

echo "🚀 Iniciando SpotShadow..."

# Verificar se FFmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ FFmpeg não encontrado. Instalando..."
    
    # Tentar instalar FFmpeg
    if command -v apt-get &> /dev/null; then
        apt-get update -y && apt-get install -y ffmpeg
    elif command -v apk &> /dev/null; then
        apk add --no-cache ffmpeg
    else
        echo "❌ Não foi possível instalar FFmpeg automaticamente"
    fi
else
    echo "✅ FFmpeg já está instalado"
fi

# Verificar instalação
ffmpeg -version

echo "🎵 Iniciando aplicação..."
python app.py