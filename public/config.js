// ============================================================================
// CONFIGURAÇÕES PROTEGIDAS DO SISTEMA
// ============================================================================

(function() {
    'use strict';
    
    // Configurações da API
    const API_CONFIG = {
        // Para desenvolvimento local
        development: {
            baseUrl: 'http://localhost:5000',
            endpoints: {
                download: '/download',
                status: '/status',
                downloadZip: '/download-zip'
            }
        },
        
        // Para produção (MUDE ESTAS URLs!)
        production: {
            baseUrl: 'https://seudominio.com',
            endpoints: {
                download: '/api/download',
                status: '/api/status',
                downloadZip: '/api/download-zip'
            }
        }
    };

    // Configurações de segurança
    const SECURITY_CONFIG = {
        allowedDomains: ['localhost', '127.0.0.1', 'seudominio.com'],
        tokenExpiry: 300000, // 5 minutos
        maxRetries: 3,
        rateLimitDelay: 1000
    };

    // Detectar ambiente
    const isProduction = window.location.hostname !== 'localhost' && 
                        window.location.hostname !== '127.0.0.1';
    const config = isProduction ? API_CONFIG.production : API_CONFIG.development;

    // Verificação de domínio
    if (!SECURITY_CONFIG.allowedDomains.includes(window.location.hostname)) {
        document.body.innerHTML = '<div style="text-align:center;padding:50px;color:red;font-size:24px;">❌ DOMÍNIO NÃO AUTORIZADO</div>';
        throw new Error('Acesso negado');
    }

    // Exportar configurações (protegidas)
    Object.defineProperty(window, 'API_CONFIG', {
        value: config,
        writable: false,
        configurable: false
    });

    Object.defineProperty(window, 'SECURITY_CONFIG', {
        value: SECURITY_CONFIG,
        writable: false,
        configurable: false
    });

    // Proteção contra modificação
    Object.freeze(window.API_CONFIG);
    Object.freeze(window.SECURITY_CONFIG);

})();