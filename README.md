# 🤖 Facebook Automation - Postagens Automáticas com IA

Sistema completo para automação de posts no Facebook usando Inteligência Artificial para geração de conteúdo.

## 🚀 Funcionalidades

- ✅ **Geração Automática de Conteúdo** com OpenAI GPT
- ✅ **Agendamento de Posts** para horários específicos  
- ✅ **Múltiplas Páginas** do Facebook
- ✅ **Templates Personalizáveis** para diferentes tipos de conteúdo
- ✅ **Dashboard Web** para gerenciamento
- ✅ **Métricas e Relatórios** de desempenho
- ✅ **Sistema de Filas** com Celery para processamento assíncrono
- ✅ **Histórico Completo** de posts publicados
- ✅ **API REST** para integração externa

## 🛠️ Tecnologias

- **Backend**: Django 5.0
- **IA**: OpenAI GPT-3.5/GPT-4
- **Social Media**: Facebook Graph API
- **Queue System**: Celery + RabbitMQ
- **Database**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Frontend**: Bootstrap 5 + jQuery

## 📋 Pré-requisitos

- Python 3.9+
- RabbitMQ Server
- Conta Facebook Developer
- Conta OpenAI
- Git

## 🚀 Instalação Rápida

### 1. Clone o Repositório

```bash
git clone <url-do-repositorio>
cd fb_automation
```

### 2. Configure o Ambiente Virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\\Scripts\\activate  # Windows
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Instale e Configure o RabbitMQ

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

#### macOS:
```bash
brew install rabbitmq
brew services start rabbitmq
```

#### Windows:
1. Baixe e instale de: https://www.rabbitmq.com/download.html
2. Inicie o serviço RabbitMQ

### 5. Configure as Variáveis de Ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas chaves de API
```

**📖 [Guia Completo de Configuração das APIs](CONFIGURACAO_APIS.md)**

### 6. Execute as Migrações

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Inicie o Servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## 🎯 Como Usar

### 1. Configurar Páginas do Facebook

1. Acesse `/admin/` e faça login
2. Vá em "Facebook Integration" → "Facebook Pages"
3. Adicione suas páginas com os tokens de acesso

### 2. Criar Templates de Conteúdo

1. No dashboard, clique em "Templates"
2. Crie templates com prompts para IA:

```
Exemplo de Prompt:
"Crie um post motivacional sobre {tema} para uma página de {categoria}. 
Use linguagem envolvente e inclua call-to-action."
```

### 3. Agendar Posts

1. Clique em "Agendar Post"
2. Escolha:
   - Página do Facebook
   - Template
   - Data e hora
3. O sistema irá gerar o conteúdo automaticamente na hora agendada

### 4. Monitorar Resultados

- **Dashboard**: Visão geral das métricas
- **Posts Publicados**: Histórico com engajamento
- **Posts Agendados**: Acompanhe o status

## 🔄 Automação Completa

### Sistema de Processamento

O sistema funciona com 3 componentes:

1. **Web Server** (Django): Interface e API
2. **Worker** (Celery): Processa tasks em background
3. **Scheduler** (Celery Beat): Executa tarefas periódicas

### Executar Componentes

```bash
# Terminal 1: Servidor Web
python manage.py runserver

# Terminal 2: Worker para processar tasks
celery -A fb_automation worker --loglevel=info

# Terminal 3: Scheduler para automação
celery -A fb_automation beat --loglevel=info

# Teste de conexão RabbitMQ
python test_rabbitmq.py
```

### Comando Manual

```bash
# Executar processamento manual
python manage.py run_automation --task=all
```

## 📊 API Endpoints

### Principais Endpoints

```
GET  /                          # Dashboard
GET  /pages/                    # Lista páginas
GET  /templates/                # Lista templates  
GET  /scheduled/                # Posts agendados
GET  /published/                # Posts publicados
POST /api/generate-content/     # Gerar prévia de conteúdo
GET  /api/test-openai/          # Testar conexão OpenAI
```

### Exemplo de Uso da API

```python
import requests

# Gerar prévia de conteúdo
response = requests.post('http://localhost:8000/api/generate-content/', json={
    'template_id': 1,
    'context': {
        'tema': 'tecnologia',
        'categoria': 'inovação'
    }
})

content = response.json()['content']
```

## 🔧 Configuração Avançada

### Variáveis de Ambiente

```env
# Facebook API
FACEBOOK_APP_ID=seu_app_id
FACEBOOK_APP_SECRET=sua_chave_secreta
FACEBOOK_ACCESS_TOKEN=token_da_pagina
FACEBOOK_PAGE_ID=id_da_pagina

# OpenAI
OPENAI_API_KEY=sua_chave_openai

# Celery/RabbitMQ
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=rpc://

# Django
SECRET_KEY=sua_chave_secreta_django
DEBUG=True
```

### Configurações de IA

No admin, configure:

- **Modelo**: gpt-3.5-turbo, gpt-4, etc.
- **Temperatura**: 0.1 (conservador) a 1.0 (criativo)
- **Max Tokens**: Limite de palavras
- **Hashtags**: Incluir automaticamente
- **Emojis**: Incluir emojis nos posts

## 📈 Monitoramento

### Logs

```bash
# Logs gerais
tail -f logs/django.log

# Logs do Celery
tail -f logs/celery.log

# Logs de erro
tail -f logs/error.log

# Ver status do RabbitMQ
sudo rabbitmqctl status

# Ver filas do RabbitMQ
sudo rabbitmqctl list_queues

# Verificar status das tasks
python manage.py shell
>>> from facebook_integration.models import ScheduledPost
>>> ScheduledPost.objects.filter(status='failed')
```

### Métricas Disponíveis

- Posts publicados por dia/mês
- Taxa de sucesso/falha
- Engajamento médio (likes, comentários, shares)
- Tempo de processamento
- Uso de tokens OpenAI

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
python manage.py test

# Testes específicos  
python manage.py test facebook_integration.tests.FacebookAPIClientTest
```

### Testes Disponíveis

- ✅ Models e validações
- ✅ Serviços (Facebook API, OpenAI)
- ✅ Views e templates
- ✅ Tasks do Celery
- ✅ Integração end-to-end

## 🚀 Deploy em Produção

### Requisitos de Produção

- PostgreSQL ou MySQL
- Redis Server
- Nginx (proxy reverso)
- Supervisor (gerenciar processos)

### Configurações para Produção

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['seudominio.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fb_automation',
        'USER': 'postgres',
        'PASSWORD': 'senha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Exemplo de Deploy com Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "fb_automation.wsgi:application"]
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Adiciona nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

- **Documentação**: [CONFIGURACAO_APIS.md](CONFIGURACAO_APIS.md)
- **Issues**: Use o GitHub Issues para reportar bugs
- **Email**: contato@seudominio.com

---

## 🎯 Roadmap

### Próximas Funcionalidades

- [ ] **Suporte ao Instagram** (Instagram Basic Display API)
- [ ] **Geração de Imagens** com DALL-E
- [ ] **Analytics Avançados** com gráficos
- [ ] **Webhook Integration** para notificações em tempo real
- [ ] **Multi-idiomas** para posts internacionais
- [ ] **A/B Testing** para otimização de conteúdo
- [ ] **Integração com Google Analytics**
- [ ] **API GraphQL** para frontend moderno
- [ ] **Mobile App** (React Native)
- [ ] **Plugin WordPress**

### Melhorias Planejadas

- [ ] **Performance**: Cache com Redis
- [ ] **Segurança**: Rate limiting e autenticação JWT
- [ ] **UX**: Interface mais moderna com React
- [ ] **DevOps**: CI/CD com GitHub Actions
- [ ] **Monitoring**: Integração com Sentry

---

⭐ **Se este projeto foi útil, deixe uma estrela no GitHub!**