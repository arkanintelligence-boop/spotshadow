#!/usr/bin/env python3
"""
SpotShadow - Versão Híbrida com múltiplas estratégias
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

app = Flask(__name__)

# Status global do download
download_status = {
    'status': 'idle',
    'progress': '',
    'zip_file': None,
    'error_message': ''
}

def try_alternative_download(song_name, output_dir):
    """Tenta baixar usando yt-dlp diretamente"""
    try:
        # Buscar no YouTube diretamente
        search_query = f"{song_name} audio"
        cmd = [
            'yt-dlp',
            f'ytsearch1:{search_query}',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '128K',
            '--output', f'{output_dir}/%(title)s.%(ext)s',
            '--no-playlist'
        ]
        
        print(f"🔍 Tentando yt-dlp para: {song_name}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"✅ Sucesso com yt-dlp: {song_name}")
            return True
        else:
            print(f"❌ Falhou yt-dlp: {song_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erro yt-dlp: {e}")
        return False

def download_playlist_hybrid(playlist_url):
    """Download híbrido com múltiplas estratégias"""
    global download_status
    
    try:
        download_status['status'] = 'downloading'
        download_status['progress'] = 'Iniciando download híbrido...'
        
        # Extrair ID da playlist
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        playlist_name = f"playlist_{playlist_id}"
        output_dir = f"downloads/{playlist_name}"
        
        # Limpar diretório anterior
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        download_status['progress'] = 'Obtendo informações da playlist...'
        
        # Primeiro: obter lista de músicas
        info_cmd = [
            'spotdl', 
            playlist_url,
            '--save-file', f'{output_dir}/playlist.spotdl',
            '--preload'
        ]
        
        subprocess.run(info_cmd, capture_output=True, text=True, timeout=60)
        
        # Ler arquivo de playlist (é um JSON, não texto simples!)
        playlist_file = Path(output_dir) / 'playlist.spotdl'
        if playlist_file.exists():
            try:
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    playlist_data = json.load(f)
                
                # Extrair informações das músicas
                songs = []
                if isinstance(playlist_data, list):
                    for song_data in playlist_data:
                        if isinstance(song_data, dict):
                            name = song_data.get('name', '')
                            artists = song_data.get('artists', [])
                            if artists and isinstance(artists, list):
                                artist_names = [artist.get('name', '') if isinstance(artist, dict) else str(artist) for artist in artists]
                                song_title = f"{' & '.join(artist_names)} - {name}"
                            else:
                                song_title = name
                            
                            if song_title:
                                songs.append(song_title)
                
                print(f"📋 Músicas extraídas do JSON: {songs}")
            except Exception as e:
                print(f"❌ Erro ao ler JSON: {e}")
                songs = []
            
            download_status['progress'] = f'Encontradas {len(songs)} músicas. Baixando...'
            
            successful_downloads = 0
            
            for i, song in enumerate(songs):
                download_status['progress'] = f'Baixando {i+1}/{len(songs)}: {song[:50]}...'
                
                # Estratégia 1: Tentar yt-dlp diretamente
                if try_alternative_download(song, output_dir):
                    successful_downloads += 1
                    continue
                
                # Estratégia 2: Tentar SpotDL com diferentes provedores
                for provider in ['soundcloud', 'bandcamp']:
                    try:
                        cmd = [
                            'spotdl', 
                            song,
                            '--output', output_dir,
                            '--audio', provider,
                            '--format', 'mp3',
                            '--bitrate', '128k'
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if result.returncode == 0:
                            successful_downloads += 1
                            break
                    except:
                        continue
            
            # Verificar arquivos baixados
            mp3_files = list(Path(output_dir).rglob('*.mp3'))
            
            if mp3_files:
                download_status['progress'] = f'Criando ZIP com {len(mp3_files)} músicas...'
                
                # Criar ZIP
                zip_name = f"downloads/{playlist_name}.zip"
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in mp3_files:
                        clean_name = file_path.name.replace('_', ' ')
                        zipf.write(file_path, clean_name)
                
                # Limpar pasta temporária
                shutil.rmtree(output_dir)
                
                download_status['status'] = 'completed'
                download_status['progress'] = f'✅ Download concluído! {len(mp3_files)} de {len(songs)} músicas baixadas.'
                download_status['zip_file'] = zip_name
            else:
                raise Exception(f'Nenhuma música foi baixada. Todas as {len(songs)} músicas falharam.')
        else:
            raise Exception('Não foi possível obter informações da playlist.')
            
    except Exception as e:
        download_status['status'] = 'error'
        download_status['error_message'] = str(e)
        download_status['progress'] = f'❌ Erro: {str(e)}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-token')
def get_token():
    return jsonify({'token': 'hybrid-token'})

@app.route('/download', methods=['POST'])
def download():
    global download_status
    
    data = request.get_json()
    playlist_url = data.get('url', '').strip()
    
    if not playlist_url or 'spotify.com/playlist/' not in playlist_url:
        return jsonify({'error': 'URL inválida'}), 400
    
    if download_status['status'] == 'downloading':
        return jsonify({'error': 'Download em andamento'}), 400
    
    # Resetar status
    download_status = {
        'status': 'downloading',
        'progress': 'Preparando download híbrido...',
        'zip_file': None,
        'error_message': ''
    }
    
    # Iniciar download em thread separada
    thread = threading.Thread(target=download_playlist_hybrid, args=(playlist_url,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Download híbrido iniciado'})

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
    
    print("🎵 SpotShadow - Versão Híbrida")
    print(f"🌐 Servidor iniciando na porta {port}")
    
    app.run(debug=False, host=host, port=port)