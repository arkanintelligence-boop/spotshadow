#!/usr/bin/env python3
"""
SpotShadow - Versão com Spotify Web Scraping (sem credenciais)
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import zipfile
import threading
from pathlib import Path
import shutil
import requests
import json
import re
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Status global do download
download_status = {
    'status': 'idle',
    'progress': '',
    'zip_file': None,
    'error_message': '',
    'current_song': '',
    'downloaded_songs': 0,
    'total_songs': 0
}

def get_playlist_info_public(playlist_url):
    """Obter informações da playlist sem API (web scraping público)"""
    try:
        # Extrair ID da playlist
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        
        # URL pública do Spotify (não precisa de autenticação)
        embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(embed_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Buscar dados JSON na página
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', response.text)
            if json_match:
                data = json.loads(json_match.group(1))
                
                # Navegar na estrutura para encontrar as músicas
                playlist_data = data.get('entities', {}).get('playlists', {})
                if playlist_data:
                    playlist = list(playlist_data.values())[0]
                    tracks = playlist.get('tracks', {}).get('items', [])
                    
                    songs = []
                    for track_item in tracks:
                        track = track_item.get('track', {})
                        if track:
                            name = track.get('name', '')
                            artists = track.get('artists', [])
                            artist_names = [artist.get('name', '') for artist in artists]
                            
                            if name and artist_names:
                                song_title = f"{' & '.join(artist_names)} - {name}"
                                songs.append(song_title)
                    
                    return songs
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao obter playlist: {e}")
        return None

def download_song_youtube(song_title, output_dir):
    """Baixar música do YouTube usando yt-dlp"""
    try:
        print(f"🎵 Baixando: {song_title}")
        
        # Comando yt-dlp otimizado
        cmd = [
            'yt-dlp',
            f'ytsearch1:{song_title} audio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '128K',
            '--output', f'{output_dir}/%(title)s.%(ext)s',
            '--no-playlist',
            '--quiet',
            '--no-warnings'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"✅ Sucesso: {song_title}")
            return True
        else:
            print(f"❌ Falhou: {song_title} - {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: {song_title}")
        return False
    except Exception as e:
        print(f"❌ Erro: {song_title} - {e}")
        return False

def download_playlist_smart(playlist_url):
    """Download inteligente usando Spotify público + YouTube"""
    global download_status
    
    try:
        download_status['status'] = 'downloading'
        download_status['progress'] = 'Obtendo informações da playlist...'
        download_status['current_song'] = ''
        download_status['downloaded_songs'] = 0
        download_status['total_songs'] = 0
        
        # Extrair ID da playlist
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        playlist_name = f"playlist_{playlist_id}"
        output_dir = f"downloads/{playlist_name}"
        
        # Limpar diretório anterior
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Obter lista de músicas
        download_status['progress'] = 'Analisando playlist do Spotify...'
        songs = get_playlist_info_public(playlist_url)
        
        if not songs:
            raise Exception('Não foi possível obter informações da playlist. Verifique se ela é pública.')
        
        download_status['total_songs'] = len(songs)
        download_status['progress'] = f'Encontradas {len(songs)} músicas. Iniciando downloads...'
        
        print(f"📋 Músicas encontradas: {songs}")
        
        successful_downloads = 0
        
        for i, song in enumerate(songs):
            download_status['current_song'] = song
            download_status['progress'] = f'Baixando {i+1}/{len(songs)}: {song[:50]}...'
            
            if download_song_youtube(song, output_dir):
                successful_downloads += 1
                download_status['downloaded_songs'] = successful_downloads
        
        # Verificar arquivos baixados
        mp3_files = list(Path(output_dir).rglob('*.mp3'))
        
        if mp3_files:
            download_status['progress'] = f'Criando ZIP com {len(mp3_files)} músicas...'
            download_status['current_song'] = 'Finalizando...'
            
            # Criar ZIP
            zip_name = f"downloads/{playlist_name}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in mp3_files:
                    # Nome mais limpo
                    clean_name = file_path.name.replace('_', ' ')
                    zipf.write(file_path, clean_name)
            
            # Limpar pasta temporária
            shutil.rmtree(output_dir)
            
            download_status['status'] = 'completed'
            download_status['progress'] = f'✅ Download concluído! {len(mp3_files)} de {len(songs)} músicas baixadas.'
            download_status['zip_file'] = zip_name
            download_status['current_song'] = ''
            
        else:
            raise Exception(f'Nenhuma música foi baixada. Todas as {len(songs)} músicas falharam.')
            
    except Exception as e:
        download_status['status'] = 'error'
        download_status['error_message'] = str(e)
        download_status['progress'] = f'❌ Erro: {str(e)}'
        download_status['current_song'] = ''

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-token')
def get_token():
    return jsonify({'token': 'smart-token'})

@app.route('/download', methods=['POST'])
def download():
    global download_status
    
    data = request.get_json()
    playlist_url = data.get('url', '').strip()
    
    if not playlist_url or 'spotify.com/playlist/' not in playlist_url:
        return jsonify({'error': 'URL inválida. Use uma URL de playlist do Spotify.'}), 400
    
    if download_status['status'] == 'downloading':
        return jsonify({'error': 'Já existe um download em andamento'}), 400
    
    # Resetar status
    download_status = {
        'status': 'downloading',
        'progress': 'Preparando download inteligente...',
        'zip_file': None,
        'error_message': '',
        'current_song': '',
        'downloaded_songs': 0,
        'total_songs': 0
    }
    
    # Iniciar download em thread separada
    thread = threading.Thread(target=download_playlist_smart, args=(playlist_url,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Download inteligente iniciado'})

@app.route('/status')
def status():
    return jsonify(download_status)

@app.route('/download-zip')
def download_zip():
    if download_status['status'] == 'completed' and download_status['zip_file']:
        zip_path = download_status['zip_file']
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))
    return jsonify({'error': 'Arquivo não encontrado'}), 404

@app.route('/favicon.png')
def favicon():
    if os.path.exists('favicon.png'):
        return send_file('favicon.png', mimetype='image/png')
    return '', 404

@app.route('/logotipo-semfundo.png')
def logo():
    if os.path.exists('logotipo-semfundo.png'):
        return send_file('logotipo-semfundo.png', mimetype='image/png')
    return '', 404

if __name__ == '__main__':
    Path('downloads').mkdir(exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("🎵 SpotShadow - Versão Inteligente")
    print("🔍 Usando Spotify público + YouTube direto")
    print(f"🌐 Servidor iniciando na porta {port}")
    
    app.run(debug=False, host=host, port=port)