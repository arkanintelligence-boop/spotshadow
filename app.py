#!/usr/bin/env python3
"""
Servidor Flask para Spotify Playlist Downloader
Interface web simples para baixar playlists
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import subprocess
import zipfile
import threading
import time
from pathlib import Path
import shutil
import re
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
import schedule

app = Flask(__name__)

# Chave de segurança (mude esta chave em produção!)
SECRET_KEY = "SUA_CHAVE_SECRETA_SUPER_FORTE_2024_MUDE_ESTA_CHAVE"
DOMAIN_WHITELIST = ["localhost", "127.0.0.1", "seudominio.com", "easypanel.host", "easypanel.io"]  # Adicione seus domínios

# Status global do download
download_status = {
    'status': 'idle',  # idle, downloading, completed, error
    'progress': '',
    'current_song': '',
    'total_songs': 0,
    'downloaded_songs': 0,
    'zip_file': None,
    'error_message': '',
    'created_at': None
}

# Lista de arquivos para limpeza automática
cleanup_files = []

def generate_security_token():
    """Gera token de segurança único"""
    timestamp = str(int(time.time()))
    random_data = secrets.token_hex(16)
    combined = f"{timestamp}:{random_data}:{SECRET_KEY}"
    return hashlib.sha256(combined.encode()).hexdigest()

def verify_security_token(token, max_age=300):  # 5 minutos
    """Verifica se o token é válido"""
    try:
        # Implementação básica - em produção use JWT
        return len(token) == 64 and token.isalnum()
    except:
        return False

def check_domain_whitelist():
    """Verifica se o domínio está na whitelist"""
    host = request.headers.get('Host', '').split(':')[0]
    # Para desenvolvimento e EasyPanel, permitir qualquer host
    if 'easypanel' in host or host.startswith('192.168') or host.startswith('10.') or host.startswith('172.'):
        return True
    return host in DOMAIN_WHITELIST

def cleanup_old_files():
    """Remove arquivos antigos (mais de 5 minutos)"""
    global cleanup_files
    current_time = datetime.now()
    
    # Limpar lista de arquivos
    files_to_remove = []
    for file_info in cleanup_files:
        if current_time - file_info['created'] > timedelta(minutes=5):
            try:
                if os.path.exists(file_info['path']):
                    os.remove(file_info['path'])
                    print(f"🗑️ Arquivo removido: {file_info['path']}")
                files_to_remove.append(file_info)
            except Exception as e:
                print(f"❌ Erro ao remover {file_info['path']}: {e}")
    
    # Remover da lista
    for file_info in files_to_remove:
        cleanup_files.remove(file_info)
    
    # Limpar pasta downloads de arquivos antigos
    downloads_dir = Path('downloads')
    if downloads_dir.exists():
        for file_path in downloads_dir.glob('*.zip'):
            try:
                # Verificar idade do arquivo
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if current_time - file_time > timedelta(minutes=5):
                    file_path.unlink()
                    print(f"🗑️ ZIP antigo removido: {file_path}")
            except Exception as e:
                print(f"❌ Erro ao remover ZIP antigo: {e}")

def schedule_cleanup():
    """Agenda limpeza automática"""
    cleanup_old_files()
    # Reagendar para 1 minuto
    threading.Timer(60, schedule_cleanup).start()

def add_file_to_cleanup(file_path):
    """Adiciona arquivo à lista de limpeza"""
    global cleanup_files
    cleanup_files.append({
        'path': file_path,
        'created': datetime.now()
    })

def install_spotdl():
    """Instala o spotDL se não estiver instalado"""
    try:
        subprocess.run(['spotdl', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'spotdl'], check=True)
            return True
        except:
            return False

def get_playlist_name(playlist_url):
    """Obtém o nome da playlist usando spotDL"""
    try:
        # Usar spotDL para obter informações da playlist
        cmd = ['spotdl', 'save', playlist_url, '--save-file', 'temp_playlist.spotdl']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists('temp_playlist.spotdl'):
            # Ler a primeira linha que contém informações da playlist
            with open('temp_playlist.spotdl', 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # Extrair nome da playlist do output do spotDL
                if 'Found' in result.stdout and 'in' in result.stdout:
                    # Exemplo: "Found 142 songs in Leandro & Leonardo – Só as antigas (Playlist)"
                    parts = result.stdout.split(' in ')
                    if len(parts) > 1:
                        playlist_info = parts[1].split('\n')[0]
                        # Remover "(Playlist)" do final
                        playlist_name = playlist_info.replace(' (Playlist)', '').strip()
                        # Limpar caracteres inválidos para nome de arquivo
                        playlist_name = re.sub(r'[<>:"/\\|?*]', '_', playlist_name)
                        os.remove('temp_playlist.spotdl')
                        return playlist_name
            
            os.remove('temp_playlist.spotdl')
    except:
        pass
    
    # Fallback: usar ID da playlist
    return playlist_url.split('/')[-1].split('?')[0]

def download_playlist_async(playlist_url):
    """Download assíncrono da playlist"""
    global download_status
    
    try:
        download_status['status'] = 'downloading'
        download_status['progress'] = 'Iniciando download...'
        
        # Extrair ID da playlist
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        
        # Obter nome real da playlist
        download_status['progress'] = 'Obtendo informações da playlist...'
        playlist_name = get_playlist_name(playlist_url)
        
        output_dir = f"downloads/playlist_{playlist_id}"
        
        # Limpar diretório anterior se existir
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        download_status['progress'] = 'Verificando playlist...'
        
        # Verificar se a playlist é acessível tentando salvar metadados
        download_status['progress'] = 'Verificando playlist...'
        
        # Comando spotDL simplificado
        cmd = [
            'spotdl',
            'download',
            playlist_url,
            '--output', output_dir,
            '--format', 'mp3',
            '--bitrate', '320k'
        ]
        
        # Executar download com timeout maior
        download_status['progress'] = 'Baixando músicas... (isso pode demorar alguns minutos)'
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 minutos timeout
        
        # Verificar se houve erro
        if process.returncode != 0:
            error_output = process.stderr or process.stdout
            if 'No songs found' in error_output:
                raise Exception('Nenhuma música encontrada na playlist. Verifique se a playlist não está vazia.')
            elif 'rate limit' in error_output.lower():
                raise Exception('Limite de requisições atingido. Tente novamente em alguns minutos.')
            elif 'private' in error_output.lower():
                raise Exception('Playlist privada. Certifique-se de que a playlist é pública.')
            elif 'not found' in error_output.lower():
                raise Exception('Playlist não encontrada. Verifique se o link está correto.')
            else:
                # Mesmo com erro, verificar se alguns arquivos foram baixados
                mp3_files = list(Path(output_dir).rglob('*.mp3'))
                if mp3_files:
                    download_status['progress'] = f'Download parcial: {len(mp3_files)} músicas baixadas (alguns erros ocorreram)'
                else:
                    raise Exception(f'Erro no download: {error_output[:200]}...' if len(error_output) > 200 else error_output)
        
        # Verificar se arquivos foram baixados
        mp3_files = list(Path(output_dir).rglob('*.mp3'))
        if not mp3_files:
            raise Exception('Nenhum arquivo MP3 foi baixado. A playlist pode estar vazia ou inacessível.')
        
        download_status['progress'] = f'Criando arquivo ZIP com {len(mp3_files)} músicas...'
        
        # Criar ZIP com nome da playlist
        zip_name = f"downloads/{playlist_name}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in mp3_files:
                arcname = file_path.name  # Apenas o nome do arquivo
                zipf.write(file_path, arcname)
        
        # Limpar pasta temporária
        shutil.rmtree(output_dir)
        
        download_status['status'] = 'completed'
        download_status['progress'] = f'Download concluído! {len(mp3_files)} músicas baixadas.'
        download_status['zip_file'] = zip_name
        download_status['created_at'] = datetime.now()
        
        # Adicionar arquivo à lista de limpeza automática
        add_file_to_cleanup(zip_name)
        
    except subprocess.TimeoutExpired:
        download_status['status'] = 'error'
        download_status['error_message'] = 'Timeout no download'
        download_status['progress'] = 'Erro: Download demorou muito tempo. Tente uma playlist menor.'
    except Exception as e:
        download_status['status'] = 'error'
        download_status['error_message'] = str(e)
        download_status['progress'] = f'Erro: {str(e)}'

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Iniciar download da playlist"""
    global download_status
    
    # Verificações de segurança
    if not check_domain_whitelist():
        return jsonify({'error': 'Acesso negado - domínio não autorizado'}), 403
    
    # Verificar rate limiting básico
    user_ip = request.remote_addr
    # Em produção, implemente rate limiting mais robusto
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400
        
    playlist_url = data.get('url', '').strip()
    security_token = data.get('token', '')
    
    if not playlist_url:
        return jsonify({'error': 'URL não fornecida'}), 400
    
    if not verify_security_token(security_token):
        return jsonify({'error': 'Token de segurança inválido'}), 403
    
    if 'spotify.com/playlist/' not in playlist_url:
        return jsonify({'error': 'URL inválida. Use uma URL de playlist do Spotify'}), 400
    
    if download_status['status'] == 'downloading':
        return jsonify({'error': 'Já existe um download em andamento'}), 400
    
    # Verificar spotDL
    if not install_spotdl():
        return jsonify({'error': 'Erro ao instalar spotDL'}), 500
    
    # Resetar status
    download_status = {
        'status': 'downloading',
        'progress': 'Preparando download...',
        'zip_file': None,
        'error_message': ''
    }
    
    # Iniciar download em thread separada
    thread = threading.Thread(target=download_playlist_async, args=(playlist_url,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Download iniciado'})

@app.route('/get-token')
def get_token():
    """Obter token de segurança"""
    if not check_domain_whitelist():
        return jsonify({'error': 'Acesso negado'}), 403
    
    token = generate_security_token()
    return jsonify({'token': token})

@app.route('/status')
def status():
    """Verificar status do download"""
    # Para health check, não verificar whitelist
    return jsonify(download_status)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'spotshadow'})

@app.route('/download-zip')
def download_zip():
    """Baixar arquivo ZIP"""
    if not check_domain_whitelist():
        return jsonify({'error': 'Acesso negado'}), 403
        
    if download_status['status'] == 'completed' and download_status['zip_file']:
        zip_path = download_status['zip_file']
        
        # Verificar se arquivo não expirou (5 minutos)
        if download_status['created_at']:
            age = datetime.now() - download_status['created_at']
            if age > timedelta(minutes=5):
                return jsonify({'error': 'Arquivo expirado. Faça um novo download.'}), 410
        
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))
    
    return jsonify({'error': 'Arquivo não encontrado'}), 404

@app.route('/favicon.png')
def favicon():
    """Servir favicon"""
    if os.path.exists('favicon.png'):
        return send_file('favicon.png', mimetype='image/png')
    return '', 404

@app.route('/logotipo-semfundo.png')
def logo():
    """Servir logotipo"""
    if os.path.exists('logotipo-semfundo.png'):
        return send_file('logotipo-semfundo.png', mimetype='image/png')
    return '', 404

if __name__ == '__main__':
    # Criar diretório de downloads
    Path('downloads').mkdir(exist_ok=True)
    Path('templates').mkdir(exist_ok=True)
    
    # Iniciar limpeza automática
    schedule_cleanup()
    
    # Configuração para produção
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("🎵 Spotify Playlist Downloader")
    print("🔒 Sistema de segurança ativado")
    print("🗑️ Limpeza automática ativada (5 minutos)")
    print(f"🌐 Servidor iniciando na porta {port}")
    print(f"🔧 Modo debug: {debug}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)