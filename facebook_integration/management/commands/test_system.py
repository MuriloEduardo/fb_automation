"""
Management command para testar configurações do sistema
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from facebook_integration.notifications import test_email_configuration
from facebook_integration.backup import get_backup_status
from facebook_integration.cache import get_cache_stats


class Command(BaseCommand):
    help = "Testa as configurações do sistema (cache, email, backup)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--component",
            type=str,
            choices=["cache", "email", "backup", "all"],
            default="all",
            help="Componente específico para testar",
        )

    def handle(self, *args, **options):
        component = options["component"]

        self.stdout.write(self.style.SUCCESS("\n=== Sistema de Testes ===\n"))

        if component in ["cache", "all"]:
            self.test_cache()

        if component in ["email", "all"]:
            self.test_email()

        if component in ["backup", "all"]:
            self.test_backup()

        self.stdout.write(self.style.SUCCESS("\n=== Testes Concluídos ===\n"))

    def test_cache(self):
        """Testa o sistema de cache Redis"""
        self.stdout.write("\n📦 Testando Cache Redis...")

        try:
            # Teste básico de set/get
            test_key = "test_key"
            test_value = "test_value"

            cache.set(test_key, test_value, 60)
            retrieved = cache.get(test_key)

            if retrieved == test_value:
                self.stdout.write(self.style.SUCCESS("  ✓ Cache funcionando"))

                # Obter estatísticas
                stats = get_cache_stats()
                self.stdout.write(f"  Backend: {stats.get('backend', 'N/A')}")

                if "total_keys" in stats:
                    self.stdout.write(f"  Total de chaves: {stats['total_keys']}")
                    self.stdout.write(f"  Hits: {stats.get('hits', 0)}")
                    self.stdout.write(f"  Misses: {stats.get('misses', 0)}")
            else:
                self.stdout.write(
                    self.style.ERROR("  ✗ Cache não está funcionando corretamente")
                )

            # Limpar chave de teste
            cache.delete(test_key)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Erro no cache: {e}"))

    def test_email(self):
        """Testa o sistema de email"""
        self.stdout.write("\n📧 Testando Configuração de Email...")

        result = test_email_configuration()

        if result["success"]:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {result['message']}"))
        else:
            self.stdout.write(self.style.WARNING(f"  ⚠ {result['message']}"))

    def test_backup(self):
        """Testa o sistema de backup"""
        self.stdout.write("\n💾 Testando Sistema de Backup...")

        try:
            status = get_backup_status()

            if status.get("enabled"):
                self.stdout.write(
                    self.style.SUCCESS("  ✓ Backup automático habilitado")
                )
                self.stdout.write(f"  Diretório: {status.get('backup_dir', 'N/A')}")
                self.stdout.write(f"  Retenção: {status.get('retention_days', 0)} dias")
                self.stdout.write(
                    f"  Total de backups: {status.get('total_backups', 0)}"
                )
                self.stdout.write(
                    f"  Tamanho total: {status.get('total_size_mb', 0):.2f} MB"
                )

                latest = status.get("latest_backup")
                if latest:
                    self.stdout.write(
                        f"  Último backup: {latest['filename']} ({latest['age_days']} dias atrás)"
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("  ⚠ Backup automático desabilitado")
                )

                if "error" in status:
                    self.stdout.write(self.style.ERROR(f"  Erro: {status['error']}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Erro no backup: {e}"))
