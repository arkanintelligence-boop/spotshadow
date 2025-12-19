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
DOMAIN_WHITELIST = ["localhost", "127.0.0.1", "seudominio.com", "railway.app", "up.railway.app"]  # Adicione seus domínios

# Status global do download
download_status = {
    'status': 'idle',  # idle, downloading, completed, error
    'progress': '',
    'current_song': '',
    'total_songs': 0,
    'downloaded_songs': 0,
    'zip_file': None,
    'error_message': '',
    'created_at': None,
    'playlist_name': ''
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
    # Para desenvolvimento, Railway e EasyPanel, permitir qualquer host
    if ('railway.app' in host or 'easypanel' in host or 
        host.startswith('192.168') or host.startswith('10.') or host.startswith('172.')):
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
    """Verifica se o spotDL está disponível"""
    try:
        result = subprocess.run(['spotdl', '--version'], check=True, capture_output=True, text=True, timeout=10)
        print(f"✅ SpotDL encontrado: {result.stdout.strip()}")
        
        # Verificar FFmpeg também
        ffmpeg_result = subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True, text=True, timeout=10)
        print(f"✅ FFmpeg encontrado")
        return True
    except Exception as e:
        print(f"❌ SpotDL ou FFmpeg não disponível: {e}")
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
    except Exception as e:
        print(f"⚠️ Erro ao obter nome da playlist: {e}")
    
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
        
        # Comando spotDL otimizado (argumentos válidos para v4.1.7)
        cmd = [
            'spotdl',
            playlist_url,
            '--output', output_dir,
            '--threads', '8',           # 8 downloads simultâneos
            '--bitrate', '192k',        # Boa qualidade mas rápido
            '--format', 'mp3'
        ]
        
        print(f"🎵 Executando comando: {' '.join(cmd)}")
        print(f"📁 Diretório de saída: {output_dir}")
        
        # Executar download com timeout maior
        download_status['progress'] = 'Baixando músicas...'
        download_status['playlist_name'] = playlist_name
        
        try:
            # Executar com streaming para capturar progresso em tempo real
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, cwd=os.getcwd(), bufsize=1, universal_newlines=True)
            
            stdout_lines = []
            stderr_lines = []
            
            # Monitorar progresso em tempo real
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stdout_lines.append(output.strip())
                    # Extrair informações de progresso
                    if 'Downloaded' in output or 'Downloading' in output:
                        # Extrair nome da música atual
                        if '"' in output:
                            song_match = re.search(r'"([^"]+)"', output)
                            if song_match:
                                download_status['current_song'] = song_match.group(1)[:50] + "..." if len(song_match.group(1)) > 50 else song_match.group(1)
                    
                    # Contar músicas baixadas
                    if 'Downloaded' in output:
                        download_status['downloaded_songs'] = len([line for line in stdout_lines if 'Downloaded' in line])
            
            # Capturar stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                stderr_lines.append(stderr_output)
            
            process.wait(timeout=300)  # 5 minutos timeout
            
            print(f"📊 SpotDL retornou código: {process.returncode}")
            if stdout_lines:
                print(f"📝 SpotDL stdout: {' '.join(stdout_lines[:5])}")
            if stderr_lines:
                print(f"⚠️ SpotDL stderr: {' '.join(stderr_lines[:3])}")
                
        except subprocess.TimeoutExpired as e:
            print(f"⏰ Timeout no comando SpotDL: {e}")
            if process:
                process.kill()
            raise
        except Exception as e:
            print(f"💥 Erro ao executar SpotDL: {e}")
            raise
        
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
        
        # Criar ZIP otimizado (compressão mais rápida)
        zip_name = f"downloads/{playlist_name}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_STORED, compresslevel=1) as zipf:  # Compressão mínima = mais rápido
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
    try:
        return render_template('index.html')
    except Exception as e:
        # Fallback: HTML inline se template não for encontrado
        print(f"⚠️ Template não encontrado: {e}")
        return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpotShadow - Spotify Playlist Downloader</title>
    <link rel="icon" href="/favicon.png" type="image/png">
    <link href="https://fonts.googleapis.com/css2?family=Circular+Std:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Circular Std', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #121212 0%, #1a1a1a 50%, #000000 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; color: #ffffff; overflow-x: hidden; }
        .background-pattern { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle at 20% 80%, rgba(29, 185, 84, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(29, 185, 84, 0.05) 0%, transparent 50%), radial-gradient(circle at 40% 40%, rgba(29, 185, 84, 0.03) 0%, transparent 50%); z-index: -1; }
        .container { background: rgba(24, 24, 24, 0.95); backdrop-filter: blur(20px); border-radius: 24px; padding: 48px 40px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05); max-width: 480px; width: 90%; text-align: center; position: relative; overflow: hidden; }
        .container::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, rgba(29, 185, 84, 0.5), transparent); }
        .logo { margin-bottom: 24px; position: relative; }
        .logo img { max-width: 120px; height: auto; filter: drop-shadow(0 8px 16px rgba(29, 185, 84, 0.3)); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .logo img:hover { transform: scale(1.05); filter: drop-shadow(0 12px 24px rgba(29, 185, 84, 0.4)); }
        h1 { margin-bottom: 8px; font-size: 32px; font-weight: 700; background: linear-gradient(135deg, #1db954, #1ed760); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.5px; }
        .subtitle { color: #b3b3b3; font-size: 16px; font-weight: 400; margin-bottom: 40px; letter-spacing: 0.1px; }
        input[type="url"] { width: 100%; padding: 16px 20px; border: 2px solid rgba(255, 255, 255, 0.1); border-radius: 50px; background: rgba(255, 255, 255, 0.05); color: #ffffff; font-size: 16px; font-weight: 400; outline: none; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); backdrop-filter: blur(10px); margin-bottom: 32px; }
        input[type="url"]::placeholder { color: #b3b3b3; }
        input[type="url"]:focus { border-color: #1db954; background: rgba(255, 255, 255, 0.08); box-shadow: 0 0 0 4px rgba(29, 185, 84, 0.1), 0 8px 32px rgba(29, 185, 84, 0.2); transform: translateY(-2px); }
        .btn { background: linear-gradient(135deg, #1db954, #1ed760); color: white; border: none; padding: 16px 32px; border-radius: 50px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); width: 100%; margin-bottom: 24px; position: relative; overflow: hidden; letter-spacing: 0.5px; text-transform: uppercase; }
        .btn::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent); transition: left 0.5s; }
        .btn:hover::before { left: 100%; }
        .btn:hover { background: linear-gradient(135deg, #1ed760, #21e065); transform: translateY(-3px); box-shadow: 0 12px 24px rgba(29, 185, 84, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1); }
        .btn:disabled { background: linear-gradient(135deg, #404040, #505050); cursor: not-allowed; transform: none; box-shadow: none; }
        .status { margin-top: 32px; padding: 24px; border-radius: 16px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); display: none; backdrop-filter: blur(10px); }
        .status.show { display: block; }
        .status.downloading { background: rgba(29, 185, 84, 0.1); border-color: rgba(29, 185, 84, 0.3); }
        .status.completed { background: rgba(76, 175, 80, 0.1); border-color: rgba(76, 175, 80, 0.3); }
        .status.error { background: rgba(244, 67, 54, 0.1); border-color: rgba(244, 67, 54, 0.3); }
        .spinner { border: 3px solid rgba(255, 255, 255, 0.1); border-top: 3px solid #1db954; border-radius: 50%; width: 32px; height: 32px; animation: spin 1s linear infinite; margin: 16px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .features { margin-top: 24px; display: flex; justify-content: space-around; gap: 16px; }
        .feature { text-align: center; flex: 1; }
        .feature-icon { font-size: 24px; margin-bottom: 8px; opacity: 0.8; }
        .feature-text { font-size: 12px; color: #b3b3b3; font-weight: 500; }
    </style>
</head>
<body>
    <div class="background-pattern"></div>
    <div class="container">
        <div class="logo">
            <img src="/logotipo-semfundo.png" alt="SpotShadow Logo" />
        </div>
        <h1>SpotShadow</h1>
        <p class="subtitle">Baixe suas playlists favoritas do Spotify</p>
        <form id="downloadForm">
            <input type="url" id="playlistUrl" placeholder="Cole o link da sua playlist aqui..." required>
            <button type="submit" class="btn" id="downloadBtn">Baixar Playlist</button>
        </form>
        <div id="status" class="status">
            <div id="spinner" class="spinner" style="display: none;"></div>
            <div id="progressText"></div>
            <button id="downloadZipBtn" class="btn" style="display: none;">📦 Baixar ZIP</button>
        </div>
        <div class="features">
            <div class="feature"><div class="feature-icon">🎵</div><div class="feature-text">Alta Qualidade</div></div>
            <div class="feature"><div class="feature-icon">⚡</div><div class="feature-text">Super Rápido</div></div>
            <div class="feature"><div class="feature-icon">🔒</div><div class="feature-text">100% Seguro</div></div>
        </div>
        <p style="margin-top: 32px; padding: 20px; background: rgba(255, 255, 255, 0.02); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05);"><strong style="color: #ffffff; font-size: 14px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; display: block;">Exemplo de URL</strong><code style="background: rgba(29, 185, 84, 0.1); color: #1ed760; padding: 8px 12px; border-radius: 8px; font-family: monospace; font-size: 13px; word-break: break-all; display: inline-block; border: 1px solid rgba(29, 185, 84, 0.2);">https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M</code></p>
    </div>
    <script>
        const form = document.getElementById('downloadForm');
        const downloadBtn = document.getElementById('downloadBtn');
        const status = document.getElementById('status');
        const spinner = document.getElementById('spinner');
        const progressText = document.getElementById('progressText');
        const downloadZipBtn = document.getElementById('downloadZipBtn');
        const playlistUrl = document.getElementById('playlistUrl');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = playlistUrl.value.trim();
            if (!url) return;

            downloadBtn.disabled = true;
            downloadBtn.textContent = 'Processando...';
            status.className = 'status show downloading';
            spinner.style.display = 'block';
            progressText.textContent = 'Iniciando download...';
            downloadZipBtn.style.display = 'none';

            try {
                const tokenResponse = await fetch('/get-token');
                const tokenData = await tokenResponse.json();
                
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, token: tokenData.token })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Erro no servidor');

                const statusInterval = setInterval(async () => {
                    try {
                        const statusResponse = await fetch('/status');
                        const statusData = await statusResponse.json();
                        progressText.textContent = statusData.progress || 'Processando...';

                        if (statusData.status === 'completed') {
                            clearInterval(statusInterval);
                            status.className = 'status show completed';
                            spinner.style.display = 'none';
                            progressText.textContent = '✅ Download concluído!';
                            downloadZipBtn.style.display = 'block';
                            downloadBtn.disabled = false;
                            downloadBtn.textContent = 'Baixar Playlist';
                        } else if (statusData.status === 'error') {
                            clearInterval(statusInterval);
                            status.className = 'status show error';
                            spinner.style.display = 'none';
                            progressText.textContent = '❌ ' + (statusData.error_message || 'Erro desconhecido');
                            downloadBtn.disabled = false;
                            downloadBtn.textContent = 'Baixar Playlist';
                        }
                    } catch (error) {
                        clearInterval(statusInterval);
                        spinner.style.display = 'none';
                        progressText.textContent = '❌ Erro ao verificar status';
                        downloadBtn.disabled = false;
                        downloadBtn.textContent = 'Baixar Playlist';
                    }
                }, 1000);

            } catch (error) {
                status.className = 'status show error';
                spinner.style.display = 'none';
                progressText.textContent = '❌ ' + error.message;
                downloadBtn.disabled = false;
                downloadBtn.textContent = 'Baixar Playlist';
            }
        });

        downloadZipBtn.addEventListener('click', () => {
            window.location.href = '/download-zip';
        });
    </script>
</body>
</html>
        """

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
    print("🔍 Verificando SpotDL...")
    if not install_spotdl():
        print("❌ Falha ao verificar/instalar SpotDL")
        return jsonify({'error': 'SpotDL não disponível. Verifique se FFmpeg está instalado.'}), 500
    print("✅ SpotDL verificado com sucesso")
    
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
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("🎵 Spotify Playlist Downloader")
    print("🔒 Sistema de segurança ativado")
    print("🗑️ Limpeza automática ativada (5 minutos)")
    print(f"🌐 Servidor iniciando na porta {port}")
    print(f"🔧 Modo debug: {debug}")
    print(f"🏠 Host: {host}")
    
    try:
        app.run(debug=debug, host=host, port=port)
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        import traceback
        traceback.print_exc()