# 📤 Guia de Publicação

## 🎯 Estrutura Final para Publicação

```
public/
├── index.html                    # Página principal
├── css/
│   └── style.css                # Estilos organizados
├── js/
│   └── script.js                # JavaScript separado
├── images/
│   ├── favicon.png              # Ícone do site
│   └── logotipo-semfundo.png    # Logo principal
├── config.js                    # Configurações da API
├── README.md                    # Documentação
└── PUBLICACAO.md               # Este guia
```

## 🚀 Passos para Publicar

### 1. **Servidor Web Estático**
Para hospedar apenas o frontend:
- Faça upload da pasta `public/` para seu servidor
- Configure o `config.js` com a URL da sua API
- Teste se todas as imagens carregam

### 2. **Netlify/Vercel (Recomendado)**
```bash
# 1. Faça upload da pasta public/
# 2. Configure as variáveis de ambiente
# 3. Ajuste config.js para produção
```

### 3. **GitHub Pages**
```bash
# 1. Crie um repositório no GitHub
# 2. Faça upload dos arquivos da pasta public/
# 3. Ative GitHub Pages nas configurações
```

## ⚙️ Configuração da API

### Desenvolvimento Local:
```javascript
baseUrl: 'http://localhost:5000'
```

### Produção:
```javascript
baseUrl: 'https://seudominio.com'
```

## 🔧 Personalização Rápida

### Alterar Cores:
Edite `css/style.css`:
```css
/* Degradê do fundo */
background: linear-gradient(to bottom, #08a901, #053912);

/* Cor dos botões */
background: #1db954;
```

### Alterar Logo:
1. Substitua `images/logotipo-semfundo.png`
2. Mantenha proporção quadrada (150x150px recomendado)

### Alterar Favicon:
1. Substitua `images/favicon.png`
2. Tamanho: 32x32px ou 64x64px

## 📱 Teste de Responsividade

Teste em:
- [ ] Desktop (Chrome, Firefox, Safari)
- [ ] Tablet (iPad, Android)
- [ ] Mobile (iPhone, Android)

## 🌐 URLs de Exemplo

### Desenvolvimento:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`

### Produção:
- Frontend: `https://seusite.com`
- Backend: `https://api.seusite.com`

## ✅ Checklist Final

- [ ] Todas as imagens carregam
- [ ] CSS e JS estão funcionando
- [ ] Favicon aparece na aba
- [ ] Site é responsivo
- [ ] API está configurada
- [ ] Testado em diferentes navegadores

## 🆘 Problemas Comuns

### Imagens não carregam:
- Verifique os caminhos em `index.html`
- Confirme se as imagens estão na pasta `images/`

### API não funciona:
- Verifique `config.js`
- Confirme se o backend está rodando
- Teste as URLs da API

### CSS não aplica:
- Verifique o caminho em `index.html`
- Confirme se `style.css` existe

## 📞 Suporte

Para problemas técnicos, verifique:
1. Console do navegador (F12)
2. Network tab para erros de API
3. Configurações do servidor