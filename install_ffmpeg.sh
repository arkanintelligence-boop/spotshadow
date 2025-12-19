#!/bin/bash
# Script para instalar FFmpeg no Railway

echo "🔧 Instalando FFmpeg..."

# Atualizar repositórios
apt-get update -y

# Instalar FFmpeg
apt-get install -y ffmpeg

# Verificar instalação
ffmpeg -version

echo "✅ FFmpeg instalado com sucesso!"