"""
Sistema de geração de relatórios PDF profissionais
"""

import io
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.widgets.markers import makeMarker

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Gerador de relatórios PDF profissionais"""

    def __init__(self, title="Relatório Facebook Automation", page_size=A4):
        self.title = title
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos customizados"""
        # Título principal
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1877F2"),  # Facebook blue
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Subtítulo
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#4267B2"),
                spaceAfter=12,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )

        # Métrica destacada
        self.styles.add(
            ParagraphStyle(
                name="MetricValue",
                parent=self.styles["Normal"],
                fontSize=32,
                textColor=colors.HexColor("#1877F2"),
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Label de métrica
        self.styles.add(
            ParagraphStyle(
                name="MetricLabel",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
        )

    def generate_page_report(self, page, start_date=None, end_date=None):
        """
        Gera relatório PDF para uma página específica

        Args:
            page: Instância de FacebookPage
            start_date: Data inicial (default: 30 dias atrás)
            end_date: Data final (default: hoje)

        Returns:
            BytesIO: Buffer com o PDF gerado
        """
        from facebook_integration.models import PublishedPost, PostMetrics

        if not end_date:
            end_date = timezone.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Criar buffer
        buffer = io.BytesIO()

        # Criar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Container para elementos
        elements = []

        # Título
        elements.append(
            Paragraph(
                f"Relatório de Performance<br/>{page.name}", self.styles["CustomTitle"]
            )
        )

        elements.append(
            Paragraph(
                f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                self.styles["Normal"],
            )
        )

        elements.append(Spacer(1, 20))

        # Buscar dados
        posts = PublishedPost.objects.filter(
            facebook_page=page, published_at__gte=start_date, published_at__lte=end_date
        )

        # Métricas gerais
        total_posts = posts.count()
        total_likes = sum(p.likes_count for p in posts)
        total_comments = sum(p.comments_count for p in posts)
        total_shares = sum(p.shares_count for p in posts)

        # Métricas estendidas das últimas coletas
        latest_metrics = PostMetrics.objects.filter(post__in=posts).order_by(
            "-collected_at"
        )[:total_posts]

        total_reach = sum(m.reach for m in latest_metrics)
        total_clicks = sum(m.post_clicks for m in latest_metrics)
        total_video_views = sum(m.video_views for m in latest_metrics)

        # Seção de métricas principais
        elements.append(
            Paragraph("📊 Métricas Principais", self.styles["CustomSubtitle"])
        )
        elements.append(Spacer(1, 10))

        # Tabela de métricas
        metrics_data = [
            ["Métrica", "Valor"],
            ["Posts Publicados", str(total_posts)],
            ["Total de Curtidas", f"{total_likes:,}"],
            ["Total de Comentários", f"{total_comments:,}"],
            ["Total de Compartilhamentos", f"{total_shares:,}"],
            ["Alcance Total", f"{total_reach:,}"],
            ["Cliques no Post", f"{total_clicks:,}"],
            ["Visualizações de Vídeo", f"{total_video_views:,}"],
        ]

        if total_posts > 0:
            avg_engagement = (total_likes + total_comments + total_shares) / total_posts
            metrics_data.append(["Engajamento Médio/Post", f"{avg_engagement:.1f}"])

        metrics_table = Table(metrics_data, colWidths=[3 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1877F2")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.lightgrey],
                    ),
                ]
            )
        )

        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Top 5 Posts
        if total_posts > 0:
            elements.append(Paragraph("🏆 Top 5 Posts", self.styles["CustomSubtitle"]))
            elements.append(Spacer(1, 10))

            top_posts = posts.order_by("-likes_count")[:5]
            top_posts_data = [["Post", "Curtidas", "Comentários", "Compartilhamentos"]]

            for post in top_posts:
                content_preview = (
                    post.content[:50] + "..."
                    if len(post.content) > 50
                    else post.content
                )
                top_posts_data.append(
                    [
                        content_preview,
                        str(post.likes_count),
                        str(post.comments_count),
                        str(post.shares_count),
                    ]
                )

            top_table = Table(
                top_posts_data, colWidths=[3 * inch, 1 * inch, 1 * inch, 1 * inch]
            )
            top_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4267B2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ]
                )
            )

            elements.append(top_table)

        elements.append(Spacer(1, 20))

        # Rodapé
        elements.append(Spacer(1, 40))
        footer_style = ParagraphStyle(
            name="Footer",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
        elements.append(
            Paragraph(
                f"Gerado em {timezone.now().strftime('%d/%m/%Y %H:%M')} | Facebook Automation System",
                footer_style,
            )
        )

        # Construir PDF
        doc.build(elements)

        # Resetar buffer
        buffer.seek(0)
        return buffer

    def generate_analytics_report(self, pages=None, days=30):
        """
        Gera relatório analítico consolidado de múltiplas páginas

        Args:
            pages: Lista de FacebookPage (None = todas)
            days: Número de dias para análise

        Returns:
            BytesIO: Buffer com o PDF gerado
        """
        from facebook_integration.models import FacebookPage, PublishedPost

        if pages is None:
            pages = FacebookPage.objects.filter(is_active=True)

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=self.page_size)
        elements = []

        # Título
        elements.append(
            Paragraph("Relatório Analítico Consolidado", self.styles["CustomTitle"])
        )
        elements.append(Paragraph(f"Últimos {days} dias", self.styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Resumo por página
        elements.append(
            Paragraph("📈 Resumo por Página", self.styles["CustomSubtitle"])
        )
        elements.append(Spacer(1, 10))

        summary_data = [["Página", "Posts", "Curtidas", "Comentários", "Compartilh."]]

        for page in pages:
            posts = PublishedPost.objects.filter(
                facebook_page=page, published_at__gte=start_date
            )

            total_posts = posts.count()
            total_likes = sum(p.likes_count for p in posts)
            total_comments = sum(p.comments_count for p in posts)
            total_shares = sum(p.shares_count for p in posts)

            summary_data.append(
                [
                    page.name[:30],
                    str(total_posts),
                    f"{total_likes:,}",
                    f"{total_comments:,}",
                    f"{total_shares:,}",
                ]
            )

        summary_table = Table(summary_data)
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1877F2")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.lightgrey],
                    ),
                ]
            )
        )

        elements.append(summary_table)

        # Rodapé
        elements.append(Spacer(1, 40))
        elements.append(
            Paragraph(
                f"Gerado em {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                self.styles["Normal"],
            )
        )

        doc.build(elements)
        buffer.seek(0)
        return buffer


def generate_page_pdf_report(page_id, start_date=None, end_date=None):
    """
    Helper function para gerar relatório de página

    Args:
        page_id: ID da página
        start_date: Data inicial
        end_date: Data final

    Returns:
        BytesIO: Buffer com o PDF
    """
    from facebook_integration.models import FacebookPage

    try:
        page = FacebookPage.objects.get(id=page_id)
        generator = PDFReportGenerator()
        return generator.generate_page_report(page, start_date, end_date)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório PDF: {e}")
        raise


def generate_consolidated_pdf_report(page_ids=None, days=30):
    """
    Helper function para gerar relatório consolidado

    Args:
        page_ids: Lista de IDs de páginas (None = todas)
        days: Número de dias

    Returns:
        BytesIO: Buffer com o PDF
    """
    from facebook_integration.models import FacebookPage

    try:
        if page_ids:
            pages = FacebookPage.objects.filter(id__in=page_ids, is_active=True)
        else:
            pages = FacebookPage.objects.filter(is_active=True)

        generator = PDFReportGenerator()
        return generator.generate_analytics_report(pages, days)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório consolidado: {e}")
        raise
