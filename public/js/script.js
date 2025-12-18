// ============================================================================
// SISTEMA DE PROTEÇÃO ANTI-CLONAGEM
// ============================================================================

// Verificação de domínio
const ALLOWED_DOMAINS = ['localhost', '127.0.0.1', 'seudominio.com'];
const currentDomain = window.location.hostname;

if (!ALLOWED_DOMAINS.includes(currentDomain)) {
    document.body.innerHTML = '<div style="text-align:center;padding:50px;color:red;font-size:24px;">❌ ACESSO NEGADO<br>Domínio não autorizado</div>';
    throw new Error('Domínio não autorizado');
}

// Proteção contra DevTools
let devtools = {open: false, orientation: null};
const threshold = 160;

setInterval(() => {
    if (window.outerHeight - window.innerHeight > threshold || 
        window.outerWidth - window.innerWidth > threshold) {
        if (!devtools.open) {
            devtools.open = true;
            console.clear();
            document.body.innerHTML = '<div style="text-align:center;padding:50px;color:red;font-size:24px;">🚫 FERRAMENTAS DE DESENVOLVEDOR DETECTADAS<br>Acesso bloqueado por segurança</div>';
        }
    }
}, 500);

// Desabilitar clique direito
document.addEventListener('contextmenu', e => e.preventDefault());

// Desabilitar teclas de desenvolvedor
document.addEventListener('keydown', e => {
    if (e.key === 'F12' || 
        (e.ctrlKey && e.shiftKey && e.key === 'I') ||
        (e.ctrlKey && e.shiftKey && e.key === 'C') ||
        (e.ctrlKey && e.key === 'u')) {
        e.preventDefault();
        alert('🚫 Função desabilitada por segurança');
    }
});

// Ofuscar código fonte
(function() {
    'use strict';
    
    // Elementos DOM
    const form = document.getElementById('downloadForm');
    const downloadBtn = document.getElementById('downloadBtn');
    const status = document.getElementById('status');
    const spinner = document.getElementById('spinner');
    const progressText = document.getElementById('progressText');
    const downloadZipBtn = document.getElementById('downloadZipBtn');
    const playlistUrl = document.getElementById('playlistUrl');

    // Variáveis de controle
    let statusInterval;
    let securityToken = null;

    // Função para obter token de segurança
    async function getSecurityToken() {
        try {
            const response = await fetch(API_CONFIG.baseUrl + '/get-token');
            const data = await response.json();
            return data.token;
        } catch (error) {
            throw new Error('Erro ao obter token de segurança');
        }
    }

    // Event listener para o formulário
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const url = playlistUrl.value.trim();
        if (!url) return;

        // Resetar interface
        downloadBtn.disabled = true;
        downloadBtn.textContent = 'Processando...';
        status.className = 'status show downloading';
        spinner.style.display = 'block';
        progressText.textContent = 'Obtendo token de segurança...';
        downloadZipBtn.style.display = 'none';

        try {
            // Obter token de segurança
            securityToken = await getSecurityToken();
            
            progressText.textContent = 'Iniciando download...';
            
            const response = await fetch(API_CONFIG.baseUrl + API_CONFIG.endpoints.download, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url: url,
                    token: securityToken
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erro no servidor');
            }

            // Iniciar polling do status
            startStatusPolling();

        } catch (error) {
            showError(error.message);
        }
    });

// Função para iniciar o polling do status
function startStatusPolling() {
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(API_CONFIG.baseUrl + API_CONFIG.endpoints.status);
            const data = await response.json();

            // Atualizar texto de progresso
            let progressMsg = data.progress;
            
            // Adicionar informações extras se disponível
            if (data.total_songs > 0) {
                progressMsg += ` (${data.downloaded_songs}/${data.total_songs})`;
            }
            
            if (data.current_song) {
                progressMsg += `\n🎵 ${data.current_song}`;
            }
            
            progressText.innerHTML = progressMsg.replace(/\n/g, '<br>');

            if (data.status === 'completed') {
                clearInterval(statusInterval);
                showCompleted();
            } else if (data.status === 'error') {
                clearInterval(statusInterval);
                showError(data.error_message || 'Erro desconhecido');
            }
        } catch (error) {
            clearInterval(statusInterval);
            showError('Erro ao verificar status');
        }
    }, 1000);
}

// Função para mostrar download concluído
function showCompleted() {
    status.className = 'status show completed';
    spinner.style.display = 'none';
    progressText.textContent = '✅ Download concluído!';
    downloadZipBtn.style.display = 'block';
    resetForm();
}

// Função para mostrar erro
function showError(message) {
    status.className = 'status show error';
    spinner.style.display = 'none';
    progressText.textContent = `❌ ${message}`;
    resetForm();
}

// Função para resetar o formulário
function resetForm() {
    downloadBtn.disabled = false;
    downloadBtn.textContent = 'Baixar Playlist';
}

// Event listener para o botão de download do ZIP
downloadZipBtn.addEventListener('click', () => {
    window.location.href = API_CONFIG.baseUrl + API_CONFIG.endpoints.downloadZip;
});

    // Auto-focus no input quando a página carrega
    document.addEventListener('DOMContentLoaded', () => {
        playlistUrl.focus();
    });

    // Expor funções necessárias globalmente (dentro da IIFE)
    window.startStatusPolling = startStatusPolling;
    window.showCompleted = showCompleted;
    window.showError = showError;
    window.resetForm = resetForm;

})(); // Fim da IIFE

// Proteção adicional - limpar console periodicamente
setInterval(() => {
    console.clear();
    console.log('%c🚫 ACESSO RESTRITO', 'color: red; font-size: 20px; font-weight: bold;');
    console.log('%cEste site é protegido contra clonagem.', 'color: red; font-size: 14px;');
}, 1000);

// Detectar tentativas de cópia do código
document.addEventListener('selectstart', e => {
    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
    }
});

// Proteção contra iframe
if (window.top !== window.self) {
    window.top.location = window.self.location;
}