#!/usr/bin/env python3
"""
SpotShadow - Spotify Playlist Downloader
Interface web elegante para baixar playlists do Spotify
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import zipfile
import threading
from pathlib import Path
import shutil

app = Flask(__name__)

# Status global do download
download_status = {
    'status': 'idle',
    'progress': '',
    'zip_file': None,
    'error_message': ''
}

def check_spotdl():
    """Verifica se o spotDL está disponível"""
    try:
        subprocess.run(['spotdl', '--version'], check=True, capture_output=True)
        return True
    except:
        return False

def get_playlist_name(playlist_url):
    """Obtém o nome da playlist"""
    return playlist_url.split('/')[-1].split('?')[0]

def download_playlist_async(playlist_url):
    """Download assíncrono da playlist"""
    global download_status
    
    try:
        download_status['status'] = 'downloading'
        download_status['progress'] = 'Iniciando download...'
        
        # Extrair ID da playlist
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        playlist_name = get_playlist_name(playlist_url)
        
        output_dir = f"downloads/playlist_{playlist_id}"
        
        # Limpar diretório anterior se existir
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        download_status['progress'] = 'Baixando músicas...'
        
        # Comando spotDL simples
        cmd = ['spotdl', 'download', playlist_url, '--output', output_dir]
        
        # Executar download
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        if process.returncode != 0:
            raise Exception('Erro no download da playlist')
        
        # Verificar arquivos baixados
        mp3_files = list(Path(output_dir).rglob('*.mp3'))
        if not mp3_files:
            raise Exception('Nenhuma música foi baixada')
        
        download_status['progress'] = f'Criando ZIP com {len(mp3_files)} músicas...'
        
        # Criar ZIP
        zip_name = f"downloads/{playlist_name}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in mp3_files:
                zipf.write(file_path, file_path.name)
        
        # Limpar pasta temporária
        shutil.rmtree(output_dir)
        
        download_status['status'] = 'completed'
        download_status['progress'] = f'Download concluído! {len(mp3_files)} músicas.'
        download_status['zip_file'] = zip_name
        
    except Exception as e:
        download_status['status'] = 'error'
        download_status['error_message'] = str(e)
        download_status['progress'] = f'Erro: {str(e)}'

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/get-token')
def get_token():
    """Obter token de segurança (simplificado)"""
    return jsonify({'token': 'simple-token'})

@app.route('/download', methods=['POST'])
def download():
    """Iniciar download da playlist"""
    global download_status
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400
        
    playlist_url = data.get('url', '').strip()
    
    if not playlist_url:
        return jsonify({'error': 'URL não fornecida'}), 400
    
    if 'spotify.com/playlist/' not in playlist_url:
        return jsonify({'error': 'URL inválida. Use uma URL de playlist do Spotify'}), 400
    
    if download_status['status'] == 'downloading':
        return jsonify({'error': 'Já existe um download em andamento'}), 400
    
    # Verificar spotDL
    if not check_spotdl():
        return jsonify({'error': 'SpotDL não disponível'}), 500
    
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

@app.route('/status')
def status():
    """Verificar status do download"""
    return jsonify(download_status)

@app.route('/download-zip')
def download_zip():
    """Baixar arquivo ZIP"""
    if download_status['status'] == 'completed' and download_status['zip_file']:
        zip_path = download_status['zip_file']
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
    
    # Configuração
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("🎵 SpotShadow - Spotify Playlist Downloader")
    print(f"🌐 Servidor iniciando na porta {port}")
    
    app.run(debug=False, host=host, port=port)