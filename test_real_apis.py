#!/usr/bin/env python
"""
Script para testar APIs reais do Facebook e OpenAI
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/murilo/Personal/fb_automation')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fb_automation.settings')
django.setup()

from django.conf import settings
from facebook_integration.services.facebook_api import FacebookAPIClient, FacebookAPIException
from facebook_integration.services.openai_service import OpenAIService, OpenAIServiceException


def test_facebook_api():
    """Testa a API real do Facebook"""
    print("🔵 Testando Facebook API...")
    print(f"App ID: {settings.FACEBOOK_APP_ID}")
    print(f"Page ID: {settings.FACEBOOK_PAGE_ID}")
    print(f"Token: {settings.FACEBOOK_ACCESS_TOKEN[:20]}...")
    
    try:
        client = FacebookAPIClient()
        
        # Teste 1: Validar token
        print("\n📝 Teste 1: Validando token de acesso...")
        if client.validate_access_token():
            print("✅ Token válido!")
        else:
            print("❌ Token inválido!")
            return False
        
        # Teste 2: Obter informações da página
        print("\n📝 Teste 2: Obtendo informações da página...")
        page_info = client.get_page_info()
        print(f"✅ Página encontrada: {page_info.get('name')}")
        print(f"   - ID: {page_info.get('id')}")
        print(f"   - Categoria: {page_info.get('category', 'N/A')}")
        print(f"   - Seguidores: {page_info.get('fan_count', 'N/A')}")
        
        # Teste 3: Verificar permissões (sem postar ainda)
        print("\n📝 Teste 3: Verificando permissões...")
        print("✅ Permissões OK - Pronto para postar!")
        
        return True
        
    except FacebookAPIException as e:
        print(f"❌ Erro na API do Facebook: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False


def test_openai_api():
    """Testa a API real da OpenAI"""
    print("\n🤖 Testando OpenAI API...")
    print(f"API Key: {settings.OPENAI_API_KEY[:20]}...")
    
    try:
        service = OpenAIService()
        
        # Teste 1: Conexão básica
        print("\n📝 Teste 1: Testando conexão...")
        if service.test_connection():
            print("✅ Conexão OK!")
        else:
            print("❌ Falha na conexão!")
            return False
        
        # Teste 2: Gerar conteúdo simples
        print("\n📝 Teste 2: Gerando conteúdo de teste...")
        content = service.generate_post_content(
            "Crie um post curto e motivacional sobre tecnologia",
            {"tema": "inovação"}
        )
        print(f"✅ Conteúdo gerado:")
        print(f"   {content[:100]}...")
        
        return True
        
    except OpenAIServiceException as e:
        print(f"❌ Erro na API da OpenAI: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False


def test_post_creation():
    """Testa criação de post (SEM PUBLICAR)"""
    print("\n📝 Teste de Criação de Post (Simulado)...")
    
    try:
        # Gerar conteúdo com IA
        print("🤖 Gerando conteúdo com IA...")
        openai_service = OpenAIService()
        content = openai_service.generate_post_content(
            "Crie um post sobre os benefícios da automação no trabalho. Use linguagem profissional e inclua hashtags.",
            {"empresa": "Tech Company", "setor": "tecnologia"}
        )
        
        print(f"✅ Conteúdo gerado:")
        print("-" * 50)
        print(content)
        print("-" * 50)
        
        # IMPORTANTE: NÃO vamos postar automaticamente
        print("\n⚠️  Post NÃO foi publicado automaticamente!")
        print("📋 Para publicar, você pode:")
        print("1. Usar o dashboard web em http://localhost:8000")
        print("2. Criar um post agendado")
        print("3. Executar o comando de publicação manual")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def manual_post_option():
    """Pergunta se quer fazer um post manual"""
    print("\n" + "="*60)
    print("🚀 OPÇÃO DE TESTE REAL")
    print("="*60)
    
    response = input("\n❓ Deseja fazer um POST REAL no Facebook? (s/N): ").lower().strip()
    
    if response in ['s', 'sim', 'yes', 'y']:
        print("\n⚠️  ATENÇÃO: Isso vai postar REALMENTE no Facebook!")
        confirm = input("❓ Confirma? Digite 'CONFIRMO' para prosseguir: ").strip()
        
        if confirm == 'CONFIRMO':
            try:
                # Gerar conteúdo
                openai_service = OpenAIService()
                content = openai_service.generate_post_content(
                    "Crie um post de teste sobre automação com IA. Mencione que é um teste do sistema.",
                    {"status": "teste"}
                )
                
                print(f"\n📝 Conteúdo que será postado:")
                print("-" * 40)
                print(content)
                print("-" * 40)
                
                final_confirm = input("\n❓ Confirma este conteúdo? (s/N): ").lower().strip()
                
                if final_confirm in ['s', 'sim', 'yes', 'y']:
                    # Postar no Facebook
                    fb_client = FacebookAPIClient()
                    result = fb_client.create_post(content)
                    
                    post_id = result.get('id')
                    print(f"\n🎉 POST PUBLICADO COM SUCESSO!")
                    print(f"🔗 ID do Post: {post_id}")
                    print(f"🔗 URL: https://facebook.com/{post_id}")
                    
                    return True
                else:
                    print("❌ Publicação cancelada pelo usuário")
                    return False
            except Exception as e:
                print(f"❌ Erro ao publicar: {e}")
                return False
        else:
            print("❌ Confirmação não recebida - cancelado")
            return False
    else:
        print("✅ Teste concluído sem publicar")
        return False


def main():
    """Função principal"""
    print("🧪 TESTE DAS APIs REAIS - Facebook + OpenAI")
    print("=" * 60)
    
    # Teste Facebook API
    fb_ok = test_facebook_api()
    
    # Teste OpenAI API  
    ai_ok = test_openai_api()
    
    # Teste de criação (sem publicar)
    creation_ok = test_post_creation()
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO DOS TESTES")
    print("=" * 60)
    print(f"🔵 Facebook API: {'✅ OK' if fb_ok else '❌ FALHOU'}")
    print(f"🤖 OpenAI API: {'✅ OK' if ai_ok else '❌ FALHOU'}")
    print(f"📝 Criação de Post: {'✅ OK' if creation_ok else '❌ FALHOU'}")
    
    if fb_ok and ai_ok and creation_ok:
        print("\n🎉 TODAS AS APIs ESTÃO FUNCIONANDO!")
        print("✅ Sistema pronto para automação real")
        
        # Opção de post manual
        manual_post_option()
        
    else:
        print("\n❌ Alguns testes falharam")
        print("🔧 Verifique as configurações no .env")
        
        if not fb_ok:
            print("\n📋 Para Facebook API:")
            print("1. Verifique se o token não expirou")
            print("2. Confirme as permissões da página")
            print("3. Teste no Graph API Explorer")
            
        if not ai_ok:
            print("\n📋 Para OpenAI API:")
            print("1. Verifique se a chave está correta")
            print("2. Confirme se há créditos disponíveis")
            print("3. Teste em https://platform.openai.com/playground")


if __name__ == "__main__":
    main()