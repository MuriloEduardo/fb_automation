#!/usr/bin/env python
"""
Script para testar conexão com RabbitMQ
"""

import sys
import os

# Adicionar o projeto ao path
sys.path.append('/home/murilo/Personal/fb_automation')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fb_automation.settings')

try:
    import django
    django.setup()
    
    from django.conf import settings
    import kombu
    
    print("🐰 Testando conexão com RabbitMQ...")
    print(f"Broker URL: {settings.CELERY_BROKER_URL}")
    
    # Testar conexão
    connection = kombu.Connection(settings.CELERY_BROKER_URL)
    
    try:
        connection.connect()
        print("✅ Conexão com RabbitMQ estabelecida com sucesso!")
        
        # Testar criação de fila
        channel = connection.channel()
        queue = channel.queue_declare(queue='test_queue', durable=False)
        print(f"✅ Fila de teste criada: {queue}")
        
        # Limpar fila de teste
        channel.queue_delete(queue='test_queue')
        print("✅ Fila de teste removida")
        
        connection.close()
        print("✅ Conexão fechada corretamente")
        
    except Exception as e:
        print(f"❌ Erro ao conectar com RabbitMQ: {e}")
        print("\n🔧 Soluções possíveis:")
        print("1. Verificar se RabbitMQ está rodando:")
        print("   sudo systemctl status rabbitmq-server")
        print("2. Iniciar RabbitMQ:")
        print("   sudo systemctl start rabbitmq-server")
        print("3. Verificar firewall na porta 5672")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("Execute: pip install kombu")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Erro geral: {e}")
    sys.exit(1)

print("\n🎉 Teste concluído com sucesso!")
print("RabbitMQ está pronto para uso com Celery!")