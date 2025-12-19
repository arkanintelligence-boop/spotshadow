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
        
        download_status['progress'] = 'Conectando ao Spotify...'
        
        # Aguardar um pouco para evitar rate limit
        import time
        time.sleep(2)
        
        # Comando spotDL mais simples e com timeout
        cmd = [
            'spotdl', 
            playlist_url, 
            '--output', output_dir,
            '--threads', '1',
            '--format', 'mp3'
        ]
        
        print(f"🎵 Executando comando: {' '.join(cmd)}")
        download_status['progress'] = 'Processando playlist...'
        
        # Executar com timeout de 10 minutos
        try:
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=600,  # 10 minutos timeout
                cwd='/app'
            )
        except subprocess.TimeoutExpired:
            print("❌ SpotDL timeout após 10 minutos")
            raise Exception('Download demorou muito (timeout de 10 minutos). Tente uma playlist menor.')
        
        print(f"✅ SpotDL finalizado com código: {process.returncode}")
        
        # Log detalhado da saída
        if process.stdout:
            print(f"📝 SpotDL stdout:\n{process.stdout}")
        if process.stderr:
            print(f"⚠️ SpotDL stderr:\n{process.stderr}")
        
        # Verificar se houve erro
        if process.returncode != 0:
            error_output = process.stderr or process.stdout or 'Erro desconhecido'
            
            # Verificar tipos específicos de erro
            if 'rate limit' in error_output.lower() or 'too many requests' in error_output.lower():
                raise Exception('YouTube está limitando as requisições. Tente novamente em alguns minutos.')
            elif 'network' in error_output.lower() or 'connection' in error_output.lower():
                raise Exception('Erro de conexão. Verifique sua internet e tente novamente.')
            else:
                raise Exception(f'Erro no SpotDL: {error_output[:300]}')
        
        download_status['progress'] = 'Verificando arquivos baixados...'
        
        # Verificar arquivos baixados
        mp3_files = list(Path(output_dir).rglob('*.mp3'))
        print(f"🎶 Arquivos MP3 encontrados: {len(mp3_files)}")
        
        if not mp3_files:
            # Verificar todos os arquivos para debug
            all_files = list(Path(output_dir).rglob('*'))
            file_names = [f.name for f in all_files if f.is_file()]
            print(f"📁 Todos os arquivos encontrados: {file_names}")
            
            if not file_names:
                raise Exception('Nenhum arquivo foi baixado. Verifique se a playlist é pública.')
            else:
                raise Exception(f'Nenhuma música MP3 foi baixada. Arquivos encontrados: {", ".join(file_names[:5])}')
        
        download_status['progress'] = f'Criando ZIP com {len(mp3_files)} músicas...'
        
        # Criar ZIP
        zip_name = f"downloads/{playlist_name}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in mp3_files:
                # Usar nome mais limpo para o arquivo no ZIP
                clean_name = file_path.name.replace('_', ' ')
                zipf.write(file_path, clean_name)
        
        # Limpar pasta temporária
        shutil.rmtree(output_dir)
        
        download_status['status'] = 'completed'
        download_status['progress'] = f'✅ Download concluído! {len(mp3_files)} músicas prontas.'
        download_status['zip_file'] = zip_name
        
        print(f"🎉 Download concluído com sucesso: {len(mp3_files)} músicas")
        
    except Exception as e:
        error_msg = str(e)
        print(f"💥 Erro no download: {error_msg}")
        
        download_status['status'] = 'error'
        download_status['error_message'] = error_msg
        download_status['progress'] = f'❌ Erro: {error_msg}'

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