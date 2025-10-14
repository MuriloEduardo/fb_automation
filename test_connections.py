#!/usr/bin/env python
"""Script para testar conexões com APIs externas"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fb_automation.settings")
django.setup()

from django.conf import settings
from facebook_integration.services.openai_service import OpenAIService
from facebook_integration.services.facebook_api import (
    FacebookAPIClient,
    FacebookAPIException,
)


def test_openai():
    """Testa conexão com OpenAI"""
    print("\n🔍 Testando OpenAI...")
    try:
        if not settings.OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY não configurada")
            return False

        service = OpenAIService()
        # Teste simples com o cliente
        response = service.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Responda apenas: teste ok"}],
            max_tokens=10,
        )

        result = response.choices[0].message.content

        if result:
            print("✅ OpenAI funcionando!")
            print(f"   Resposta: {result[:100]}")
            return True
        else:
            print("❌ OpenAI não retornou resposta")
            return False

    except Exception as e:
        print(f"❌ Erro ao testar OpenAI: {str(e)[:200]}")
        return False


def test_gemini():
    """Testa conexão com Google Gemini"""
    print("\n🔍 Testando Google Gemini...")
    try:
        if not settings.GEMINI_API_KEY:
            print("⚠️  GEMINI_API_KEY não configurada (opcional)")
            return None

        # Teste básico da biblioteca
        try:
            from google import genai

            print("✅ Biblioteca google-genai disponível")
            return True
        except ImportError:
            print("⚠️  Biblioteca google-genai não instalada (opcional)")
            return None

    except Exception as e:
        print(f"❌ Erro ao testar Gemini: {str(e)[:200]}")
        return False


def test_facebook():
    """Testa conexão com Facebook Graph API"""
    print("\n🔍 Testando Facebook Graph API...")
    try:
        if not settings.FACEBOOK_ACCESS_TOKEN or not settings.FACEBOOK_PAGE_ID:
            print("⚠️  FACEBOOK_ACCESS_TOKEN ou FACEBOOK_PAGE_ID não configurados")
            return False

        client = FacebookAPIClient()
        page_info = client.get_page_info()

        if page_info:
            print("✅ Facebook API funcionando!")
            print(f"   Página: {page_info.get('name', 'N/A')}")
            print(f"   ID: {page_info.get('id', 'N/A')}")
            print(f"   Seguidores: {page_info.get('followers_count', 'N/A')}")
            return True
        else:
            print("❌ Facebook API não retornou dados")
            return False

    except FacebookAPIException as e:
        print(f"❌ Erro ao testar Facebook API: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)[:200]}")
        return False


def test_database():
    """Testa conexão com banco de dados"""
    print("\n🔍 Testando Banco de Dados...")
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        if result:
            print("✅ Banco de dados funcionando!")
            print(f"   Engine: {settings.DATABASES['default']['ENGINE']}")

            # Testar contagem de tabelas
            from facebook_integration.models import FacebookPage, PostTemplate

            pages_count = FacebookPage.objects.count()
            templates_count = PostTemplate.objects.count()
            print(f"   Páginas cadastradas: {pages_count}")
            print(f"   Templates cadastrados: {templates_count}")
            return True
        else:
            print("❌ Banco de dados não respondeu")
            return False

    except Exception as e:
        print(f"❌ Erro ao testar banco: {str(e)[:200]}")
        return False


def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("�� TESTE DE CONEXÕES - Facebook Automation")
    print("=" * 60)

    results = {
        "database": test_database(),
        "openai": test_openai(),
        "gemini": test_gemini(),
        "facebook": test_facebook(),
    }

    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

    for service, result in results.items():
        if result is True:
            status = "✅ OK"
        elif result is False:
            status = "❌ FALHOU"
        else:
            status = "⚠️  NÃO CONFIGURADO"
        print(f"{status.ljust(20)} {service.upper()}")

    # Calcular sucesso geral
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    total = len([r for r in results.values() if r is not None])

    print("\n" + "=" * 60)
    if failed == 0 and passed > 0:
        print("✅ Todos os testes configurados passaram!")
    elif failed > 0:
        print(f"⚠️  {passed}/{total} testes passaram, {failed} falharam")
    else:
        print("⚠️  Nenhum teste foi executado - verifique as configurações")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
