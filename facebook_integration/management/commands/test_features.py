"""
Management command para testar novas funcionalidades
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Testa as novas funcionalidades implementadas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--feature",
            type=str,
            choices=["metrics", "pdf", "approval", "all"],
            default="all",
            help="Funcionalidade específica para testar",
        )

    def handle(self, *args, **options):
        feature = options["feature"]

        self.stdout.write(
            self.style.SUCCESS("\n=== Teste de Novas Funcionalidades ===\n")
        )

        if feature in ["metrics", "all"]:
            self.test_extended_metrics()

        if feature in ["pdf", "all"]:
            self.test_pdf_reports()

        if feature in ["approval", "all"]:
            self.test_approval_workflow()

        self.stdout.write(self.style.SUCCESS("\n=== Testes Concluídos ===\n"))

    def test_extended_metrics(self):
        """Testa coleta de métricas estendidas"""
        self.stdout.write("\n📊 Testando Métricas Estendidas...")

        from facebook_integration.models import PostMetrics

        # Verificar campos novos no modelo
        fields = [f.name for f in PostMetrics._meta.get_fields()]
        new_fields = [
            "post_clicks",
            "post_clicks_unique",
            "viral_impressions",
            "video_views",
            "video_views_unique",
            "reactions_count",
        ]

        for field in new_fields:
            if field in fields:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Campo {field} presente"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Campo {field} ausente"))

        # Contar métricas coletadas
        total_metrics = PostMetrics.objects.count()
        metrics_with_clicks = PostMetrics.objects.filter(post_clicks__gt=0).count()
        metrics_with_video = PostMetrics.objects.filter(video_views__gt=0).count()

        self.stdout.write(f"  Total de métricas: {total_metrics}")
        self.stdout.write(f"  Métricas com cliques: {metrics_with_clicks}")
        self.stdout.write(f"  Métricas com vídeo: {metrics_with_video}")

        if total_metrics > 0:
            # Última métrica coletada
            latest = PostMetrics.objects.latest("collected_at")
            self.stdout.write(f"\n  Última coleta: {latest.collected_at}")
            self.stdout.write(f"    - Cliques: {latest.post_clicks}")
            self.stdout.write(f"    - Impressões virais: {latest.viral_impressions}")
            self.stdout.write(f"    - Views de vídeo: {latest.video_views}")
            self.stdout.write(f"    - Reações: {latest.reactions_count}")

    def test_pdf_reports(self):
        """Testa geração de relatórios PDF"""
        self.stdout.write("\n📄 Testando Relatórios PDF...")

        try:
            import reportlab

            self.stdout.write(self.style.SUCCESS("  ✓ reportlab instalado"))
            self.stdout.write(f"  Versão: {reportlab.Version}")
        except ImportError:
            self.stdout.write(self.style.ERROR("  ✗ reportlab não instalado"))
            self.stdout.write("    Execute: pip install reportlab")
            return

        from facebook_integration.models import FacebookPage
        from facebook_integration.reports import PDFReportGenerator

        active_pages = FacebookPage.objects.filter(is_active=True)

        if not active_pages.exists():
            self.stdout.write(self.style.WARNING("  ⚠ Nenhuma página ativa encontrada"))
            return

        # Testar geração de relatório
        page = active_pages.first()
        self.stdout.write(f"  Testando relatório para: {page.name}")

        try:
            generator = PDFReportGenerator()
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)

            pdf_buffer = generator.generate_page_report(page, start_date, end_date)
            pdf_size = len(pdf_buffer.getvalue())

            self.stdout.write(self.style.SUCCESS(f"  ✓ PDF gerado com sucesso"))
            self.stdout.write(f"  Tamanho: {pdf_size / 1024:.2f} KB")

            # Salvar PDF de teste
            test_file = f"/tmp/test_report_{page.id}.pdf"
            with open(test_file, "wb") as f:
                f.write(pdf_buffer.getvalue())
            self.stdout.write(f"  Salvo em: {test_file}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Erro ao gerar PDF: {e}"))

    def test_approval_workflow(self):
        """Testa sistema de aprovação"""
        self.stdout.write("\n✅ Testando Workflow de Aprovação...")

        from facebook_integration.models import ScheduledPost

        # Verificar campos novos
        fields = [f.name for f in ScheduledPost._meta.get_fields()]
        approval_fields = [
            "requires_approval",
            "approved_by",
            "approved_at",
            "rejection_reason",
        ]

        for field in approval_fields:
            if field in fields:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Campo {field} presente"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Campo {field} ausente"))

        # Verificar novos status
        status_choices = dict(ScheduledPost.STATUS_CHOICES)
        approval_statuses = ["pending_approval", "approved", "rejected"]

        for status in approval_statuses:
            if status in status_choices:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Status "{status}" presente'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ Status "{status}" ausente'))

        # Estatísticas
        total_posts = ScheduledPost.objects.count()
        posts_with_approval = ScheduledPost.objects.filter(
            requires_approval=True
        ).count()
        pending_approval = ScheduledPost.objects.filter(
            status="pending_approval"
        ).count()
        approved_posts = ScheduledPost.objects.filter(approved_by__isnull=False).count()

        self.stdout.write(f"\n  Total de posts: {total_posts}")
        self.stdout.write(f"  Posts com aprovação: {posts_with_approval}")
        self.stdout.write(f"  Aguardando aprovação: {pending_approval}")
        self.stdout.write(f"  Posts aprovados: {approved_posts}")

        if pending_approval > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n  ⚠ Há {pending_approval} posts aguardando aprovação!"
                )
            )
