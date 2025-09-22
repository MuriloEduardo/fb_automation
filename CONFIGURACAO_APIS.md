# 📘 Guia de Configuração - Facebook Automation

Este guia vai te orientar sobre como obter todas as chaves de API necessárias para o funcionamento completo do sistema de automação de posts no Facebook.

## 📋 Resumo das APIs Necessárias

1. **Facebook Graph API** - Para publicar posts nas páginas
2. **OpenAI API** - Para gerar conteúdo automático com IA

---

## 🔵 Facebook Graph API

### Passo 1: Criar uma Aplicação no Facebook

1. **Acesse o Facebook Developers**
   - Vá para: https://developers.facebook.com/
   - Faça login com sua conta Facebook

2. **Criar Nova Aplicação**
   - Clique em "Minhas Apps" → "Criar App"
   - Escolha "Negócios" como tipo de aplicação
   - Preencha:
     - **Nome do App**: `Meu Facebook Automation`
     - **Email de Contato**: seu email
     - **Finalidade do App**: Escolha "Você mesmo ou sua própria empresa"

3. **Configurar Produtos**
   - No painel da aplicação, adicione o produto "Facebook Login"
   - Adicione também "Webhooks" (opcional, para notificações)

### Passo 2: Configurar Permissões

1. **Facebook Login → Configurações**
   - **URIs de redirecionamento OAuth válidos**: 
     ```
     http://localhost:8000/admin/
     https://seudominio.com/admin/
     ```

2. **Configurações Básicas**
   - Anote o **ID do App** e **Chave Secreta do App**
   - Domínios do App: `localhost`, `seudominio.com`

### Passo 3: Obter Token de Acesso

#### 3.1 Token de Usuário (Temporário)

1. **Graph API Explorer**
   - Acesse: https://developers.facebook.com/tools/explorer/
   - Selecione sua aplicação no dropdown
   - Clique em "Gerar Token de Acesso"
   - Marque as permissões:
     ```
     pages_manage_posts
     pages_read_engagement  
     pages_show_list
     publish_pages
     ```

#### 3.2 Token da Página (Permanente)

1. **Usando o Token de Usuário**
   - No Graph API Explorer, execute:
     ```
     GET /me/accounts?fields=id,name,access_token
     ```
   - Copie o `access_token` da página desejada
   - Este token não expira (enquanto o app tiver permissões)

2. **Obter ID da Página**
   - No Graph API Explorer:
     ```
     GET /{nome-da-pagina}?fields=id,name
     ```
   - Ou vá na página e copie o ID da URL

### Passo 4: Valores para o .env

```env
FACEBOOK_APP_ID=123456789012345
FACEBOOK_APP_SECRET=abc123def456ghi789jkl012mno345pq
FACEBOOK_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FACEBOOK_PAGE_ID=123456789012345
```

---

## 🤖 OpenAI API

### Passo 1: Criar Conta na OpenAI

1. **Registrar**
   - Vá para: https://platform.openai.com/
   - Crie uma conta ou faça login

2. **Configurar Pagamento**
   - Vá em "Billing" → "Payment methods"
   - Adicione um cartão de crédito
   - Defina limites de uso se desejar

### Passo 2: Gerar Chave de API

1. **API Keys**
   - Vá em "API Keys" no menu lateral
   - Clique em "Create new secret key"
   - Nomeie como "Facebook Automation"
   - **⚠️ IMPORTANTE**: Copie a chave imediatamente (não será mostrada novamente)

### Passo 3: Configurar Organização (Opcional)

1. **Organizations**
   - Se estiver em uma organização, anote o Organization ID
   - Vá em "Settings" → "Organization" → "Organization ID"

### Passo 4: Valores para o .env

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## ⚙️ Configuração Final

### 1. Atualizar arquivo .env

Copie o arquivo `.env` na raiz do projeto e substitua os valores:

```env
# Facebook API Configuration
FACEBOOK_APP_ID=SEU_APP_ID_AQUI
FACEBOOK_APP_SECRET=SUA_CHAVE_SECRETA_AQUI  
FACEBOOK_ACCESS_TOKEN=SEU_TOKEN_DA_PAGINA_AQUI
FACEBOOK_PAGE_ID=ID_DA_SUA_PAGINA_AQUI

# OpenAI API Configuration
OPENAI_API_KEY=SUA_CHAVE_OPENAI_AQUI

# Celery Configuration
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=rpc://

# Django Secret Key
SECRET_KEY=django-insecure-zk)_pze+=t3tf9ha53k&=%m$5g)(^9f8&*nb6meydcj9qr_bk!
```

### 2. Testar Configurações

Execute o servidor Django:

```bash
python manage.py runserver
```

Acesse http://localhost:8000 e:

1. **Teste OpenAI**: Clique no botão "Testar IA" no dashboard
2. **Teste Facebook**: Vá em "Páginas" e teste a conexão

---

## 🚀 Executando o Sistema

### 1. Servidor Web

```bash
# Terminal 1 - Servidor Django
python manage.py runserver
```

### 2. Worker do Celery (Opcional)

```bash
# Terminal 2 - Para processamento automático
celery -A fb_automation worker --loglevel=info
```

### 3. Scheduler do Celery (Opcional)

```bash
# Terminal 3 - Para agendamento automático
celery -A fb_automation beat --loglevel=info
```

### 4. Comando Manual

```bash
# Executar tasks manualmente
python manage.py run_automation --task=all
```

---

## 🔧 Troubleshooting

### Problemas Comuns

#### Facebook API

**Erro: "Token de acesso inválido"**
- Regenere o token da página
- Verifique se as permissões estão corretas
- Confirme que o token é da página, não do usuário

**Erro: "Permissões insuficientes"**
- Certifique-se de ter as permissões: `pages_manage_posts`, `publish_pages`
- Re-autorize o app com as permissões corretas

#### OpenAI API

**Erro: "API key inválida"**
- Verifique se copiou a chave completa
- Confirme que não há espaços extras
- Gere uma nova chave se necessário

**Erro: "Quota exceeded"**
- Verifique seu limite de uso em https://platform.openai.com/usage
- Adicione créditos se necessário

#### RabbitMQ

**Erro: "Connection refused"**
- Verifique se o RabbitMQ está rodando: `sudo systemctl status rabbitmq-server`
- Inicie o serviço: `sudo systemctl start rabbitmq-server`
- Verifique a porta: RabbitMQ usa porta 5672 por padrão

**Erro: "Authentication failed"**
- Use as credenciais padrão: guest/guest
- Para produção, crie usuário específico:
  ```bash
  sudo rabbitmqctl add_user fb_automation senha123
  sudo rabbitmqctl set_permissions -p / fb_automation ".*" ".*" ".*"
  ```

### Logs Úteis

```bash
# Ver logs do Django
tail -f logs/django.log

# Ver logs do Celery  
tail -f logs/celery.log

# Verificar status das tasks
python manage.py shell
>>> from facebook_integration.models import ScheduledPost
>>> ScheduledPost.objects.filter(status='failed')
```

---

## 📞 Suporte

Se precisar de ajuda:

1. **Verifique os logs** primeiro
2. **Teste as APIs individualmente** no dashboard
3. **Confirme as configurações** no arquivo .env
4. **Consulte a documentação oficial**:
   - [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
   - [OpenAI API](https://platform.openai.com/docs/)

---

## 🔒 Segurança

### Importantes:

- **NUNCA** commite o arquivo `.env` no Git
- **Use tokens específicos** por página (não token de usuário global)
- **Configure limites** de uso nas APIs
- **Monitore** os logs regularmente
- **Rotate** as chaves periodicamente