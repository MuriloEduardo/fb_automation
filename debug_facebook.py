#!/usr/bin/env python
"""
Script para diagnosticar problemas com Facebook API
"""

import os
import sys
import django

sys.path.append('/home/murilo/Personal/fb_automation')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fb_automation.settings')
django.setup()

from django.conf import settings
import requests


def test_facebook_token_debug():
    """Testa e diagnostica o token do Facebook"""
    print("🔍 Diagnosticando Facebook API...")
    
    token = settings.FACEBOOK_ACCESS_TOKEN
    page_id = settings.FACEBOOK_PAGE_ID
    
    print(f"📋 Token: {token[:30]}...")
    print(f"📋 Page ID: {page_id}")
    
    # 1. Verificar token de usuário
    print("\n📝 Teste 1: Verificando token de usuário...")
    try:
        url = "https://graph.facebook.com/v18.0/me"
        params = {'access_token': token}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token de usuário válido: {data.get('name')}")
        else:
            print(f"❌ Token de usuário inválido: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # 2. Listar páginas do usuário
    print("\n📝 Teste 2: Listando páginas do usuário...")
    try:
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            'access_token': token,
            'fields': 'id,name,access_token,category'
        }
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get('data', [])
            print(f"✅ Encontradas {len(pages)} páginas:")
            
            for page in pages:
                print(f"   📄 {page['name']} (ID: {page['id']})")
                if page['id'] == page_id:
                    print("   ⭐ Esta é a página configurada!")
                    
                    # Testar com token da página
                    print(f"\n📝 Teste 3: Testando token da página {page['name']}...")
                    page_token = page['access_token']
                    
                    page_url = f"https://graph.facebook.com/v18.0/{page['id']}"
                    page_params = {
                        'access_token': page_token,
                        'fields': 'id,name,category,fan_count'
                    }
                    
                    page_response = requests.get(page_url, params=page_params)
                    
                    if page_response.status_code == 200:
                        page_data = page_response.json()
                        print(f"✅ Página acessível: {page_data.get('name')}")
                        print(f"   - Categoria: {page_data.get('category', 'N/A')}")
                        print(f"   - Seguidores: {page_data.get('fan_count', 'N/A')}")
                        
                        # Mostrar token correto para usar
                        print(f"\n🔑 TOKEN CORRETO PARA USAR:")
                        print(f"FACEBOOK_ACCESS_TOKEN={page_token}")
                        print(f"FACEBOOK_PAGE_ID={page['id']}")
                        
                    else:
                        print(f"❌ Erro ao acessar página: {page_response.text}")
        else:
            print(f"❌ Erro ao listar páginas: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # 3. Verificar permissões do token atual
    print("\n📝 Teste 4: Verificando permissões...")
    try:
        url = f"https://graph.facebook.com/v18.0/{token}"
        params = {'fields': 'scopes'}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            scopes = data.get('scopes', [])
            print(f"✅ Permissões do token: {', '.join(scopes)}")
            
            required_scopes = ['pages_manage_posts', 'pages_read_engagement', 'publish_pages']
            missing_scopes = [scope for scope in required_scopes if scope not in scopes]
            
            if missing_scopes:
                print(f"⚠️  Permissões faltando: {', '.join(missing_scopes)}")
            else:
                print("✅ Todas as permissões necessárias estão presentes")
        else:
            print(f"❌ Erro ao verificar permissões: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")


def suggest_fixes():
    """Sugere correções"""
    print("\n" + "="*60)
    print("🔧 SUGESTÕES DE CORREÇÃO")
    print("="*60)
    
    print("\n📋 Se o token de usuário é inválido:")
    print("1. Vá para https://developers.facebook.com/tools/explorer/")
    print("2. Selecione sua aplicação")
    print("3. Gere um novo token com as permissões:")
    print("   - pages_manage_posts")
    print("   - pages_read_engagement") 
    print("   - publish_pages")
    
    print("\n📋 Se a página não foi encontrada:")
    print("1. Certifique-se que você é admin da página")
    print("2. Use o ID correto da página (visto no teste acima)")
    print("3. Use o token da PÁGINA, não do usuário")
    
    print("\n📋 Para obter token da página:")
    print("1. No Graph API Explorer, execute:")
    print("   GET /me/accounts?fields=id,name,access_token")
    print("2. Copie o access_token da página desejada")
    print("3. Atualize o .env com o token da página")


if __name__ == "__main__":
    test_facebook_token_debug()
    suggest_fixes()