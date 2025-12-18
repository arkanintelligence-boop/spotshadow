# 🎵 SpotShadow - Spotify Playlist Downloader

Um downloader profissional de playlists do Spotify com interface web moderna e sistema de segurança robusto.

## ✨ Características

- 🎵 **Download completo** de playlists do Spotify
- 🎧 **Qualidade MP3 320kbps** 
- 🌐 **Interface web moderna** e responsiva
- 📦 **ZIP automático** com nome da playlist
- 🔒 **Sistema de segurança** anti-clonagem
- 🗑️ **Limpeza automática** (arquivos removidos em 5min)
- ⚡ **Progresso em tempo real**

## 🚀 Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/arkanintelligence-boop/spotshadow.git
cd spotshadow

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor
python app.py
```

## 🎯 Como Usar

1. **Execute o servidor**: `python app.py`
2. **Abra o navegador**: `http://localhost:5000`
3. **Cole o link** da playlist do Spotify
4. **Aguarde o download** e baixe o ZIP

## 📁 Estrutura

```
spotshadow/
├── app.py              # Servidor Flask principal
├── public/             # Frontend para publicação
│   ├── index.html     # Interface web
│   ├── css/           # Estilos
│   ├── js/            # JavaScript
│   └── images/        # Logo e favicon
└── requirements.txt   # Dependências Python
```

## 🔒 Segurança

- **Limpeza automática** de arquivos (5min)
- **Whitelist de domínios** autorizados
- **Tokens de segurança** únicos
- **Proteção anti-clonagem**
- **Rate limiting** integrado

## ⚙️ Configuração

Antes de usar em produção, altere no `app.py`:

```python
SECRET_KEY = "SUA_CHAVE_SECRETA"
DOMAIN_WHITELIST = ["localhost", "seudominio.com"]
```

E no `public/config.js`:

```javascript
allowedDomains: ['localhost', 'seudominio.com']
baseUrl: 'https://seudominio.com'
```

## 🛠️ Tecnologias

- **Backend**: Python, Flask, spotDL
- **Frontend**: HTML5, CSS3, JavaScript
- **Download**: spotDL + yt-dlp
- **Segurança**: Múltiplas camadas de proteção

## 📋 Requisitos

- Python 3.7+
- FFmpeg (instalado automaticamente)
- Conexão com internet

## 📄 Licença

Este projeto é apenas para uso educacional. Respeite os direitos autorais.

---

**Desenvolvido com ❤️ por [Arkan Intelligence](https://github.com/arkanintelligence-boop)**