#!/usr/bin/env python
"""
Script para obter o token correto da página
"""

import os
import sys
import django

sys.path.append('/home/murilo/Personal/fb_automation')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fb_automation.settings')
django.setup()

from django.conf import settings
import requests


def get_page_token():
    """Obtém o token específico da página"""
    print("🔑 Obtendo token da página...")
    
    user_token = settings.FACEBOOK_ACCESS_TOKEN
    page_id = settings.FACEBOOK_PAGE_ID
    
    try:
        # Listar páginas e seus tokens
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            'access_token': user_token,
            'fields': 'id,name,access_token'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get('data', [])
            
            for page in pages:
                if page['id'] == page_id:
                    page_token = page['access_token']
                    print(f"✅ Token da página encontrado!")
                    print(f"📄 Página: {page['name']}")
                    print(f"🔑 Token: {page_token[:30]}...")
                    
                    # Atualizar .env
                    env_content = f"""# Facebook API Configuration
FACEBOOK_APP_ID={settings.FACEBOOK_APP_ID}
FACEBOOK_APP_SECRET={settings.FACEBOOK_APP_SECRET}
FACEBOOK_ACCESS_TOKEN={page_token}
FACEBOOK_PAGE_ID={page_id}

# OpenAI API Configuration
OPENAI_API_KEY={settings.OPENAI_API_KEY}

# Celery Configuration
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=rpc://

# Django Secret Key (generate a new one for production)
SECRET_KEY=django-insecure-zk)_pze+=t3tf9ha53k&=%m$5g)(^9f8&*nb6meydcj9qr_bk!"""
                    
                    with open('/home/murilo/Personal/fb_automation/.env', 'w') as f:
                        f.write(env_content)
                    
                    print(f"✅ Arquivo .env atualizado com token da página!")
                    
                    # Testar o novo token
                    print(f"\n📝 Testando novo token...")
                    test_url = f"https://graph.facebook.com/v18.0/{page_id}"
                    test_params = {
                        'access_token': page_token,
                        'fields': 'id,name,category'
                    }
                    test_response = requests.get(test_url, params=test_params, timeout=10)
                    
                    if test_response.status_code == 200:
                        test_data = test_response.json()
                        print(f"✅ Token funcionando: {test_data.get('name')}")
                        return True
                    else:
                        print(f"❌ Token não funcionou: {test_response.text}")
                        return False
            
            print(f"❌ Página {page_id} não encontrada nas suas páginas")
            return False
        else:
            print(f"❌ Erro ao listar páginas: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    get_page_token()