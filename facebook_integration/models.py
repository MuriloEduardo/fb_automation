from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Importar modelos de grupos
from .models_groups import FacebookGroup, GroupPost


class Lead(models.Model):
    """Leads capturados de formulários do Facebook"""

    STATUS_CHOICES = [
        ("new", "Novo"),
        ("contacted", "Contatado"),
        ("qualified", "Qualificado"),
        ("converted", "Convertido"),
        ("lost", "Perdido"),
    ]

    page = models.ForeignKey(
        "FacebookPage",
        on_delete=models.CASCADE,
        related_name="leads",
        verbose_name="Página",
    )

    lead_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="ID do Lead (Facebook)"
    )

    form_id = models.CharField(
        max_length=100,
        verbose_name="ID do Formulário"
    )
    form_name = models.CharField(
        max_length=255,
        verbose_name="Nome do Formulário"
    )

    is_organic = models.BooleanField(
        default=True,
        verbose_name="Lead Orgânico"
    )

    ad_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ID do Anúncio"
    )
    ad_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nome do Anúncio"
    )

    campaign_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ID da Campanha"
    )
    campaign_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nome da Campanha"
    )

    contact_fields = models.JSONField(
        default=dict,
        verbose_name="Campos do Contato"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        verbose_name="Status"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )

    created_time = models.DateTimeField(
        verbose_name="Data de Criação (Facebook)"
    )
    collected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Coletado em"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-created_time"]
        indexes = [
            models.Index(fields=["page", "-created_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["lead_id"]),
        ]

    def __str__(self):
        email = self.contact_fields.get("email", "Sem email")
        return f"Lead {email} - {self.form_name}"

    def get_contact_name(self):
        return (
            self.contact_fields.get("full_name") or
            self.contact_fields.get("first_name") or
            "Nome não informado"
        )

    def get_contact_email(self):
        return self.contact_fields.get("email", "Email não informado")

    def get_contact_phone(self):
        return (
            self.contact_fields.get("phone_number") or
            self.contact_fields.get("phone") or
            "Telefone não informado"
        )


class FacebookPage(models.Model):
    """Model para armazenar informações das páginas do Facebook"""

    name = models.CharField(max_length=255, verbose_name="Nome da Página")
    page_id = models.CharField(max_length=100, unique=True, verbose_name="ID da Página")
    access_token = models.TextField(verbose_name="Token de Acesso")
    category = models.CharField(max_length=255, blank=True, verbose_name="Categoria")
    followers_count = models.IntegerField(default=0, verbose_name="Seguidores")

    # Permissões disponíveis
    can_publish = models.BooleanField(default=False, verbose_name="Pode Publicar")
    can_read_insights = models.BooleanField(
        default=False, verbose_name="Pode Ler Métricas"
    )
    can_manage_ads = models.BooleanField(
        default=False, verbose_name="Pode Gerenciar Anúncios"
    )

    # Status e configurações
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    auto_sync = models.BooleanField(
        default=True, verbose_name="Sincronização Automática"
    )
    auto_posting_enabled = models.BooleanField(
        default=False, verbose_name="Postagem Automática Habilitada"
    )
    last_sync = models.DateTimeField(
        null=True, blank=True, verbose_name="Última Sincronização"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Página do Facebook"
        verbose_name_plural = "Páginas do Facebook"

    def __str__(self):
        return self.name


class PostTemplate(models.Model):
    """Model para templates de posts que serão usados pela IA"""

    name = models.CharField(max_length=255, verbose_name="Nome do Template")
    prompt = models.TextField(verbose_name="Prompt para IA")
    category = models.CharField(max_length=100, verbose_name="Categoria")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template de Post"
        verbose_name_plural = "Templates de Posts"

    def __str__(self):
        return self.name


class ScheduledPost(models.Model):
    """Model para posts agendados"""

    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("generating", "Gerando Conteúdo"),
        ("ready", "Pronto para Publicar"),
        ("pending_approval", "Aguardando Aprovação"),
        ("approved", "Aprovado"),
        ("rejected", "Rejeitado"),
        ("publishing", "Publicando"),
        ("published", "Publicado"),
        ("failed", "Falhou"),
        ("cancelled", "Cancelado"),
    ]

    facebook_page = models.ForeignKey(FacebookPage, on_delete=models.CASCADE)
    template = models.ForeignKey(
        PostTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Template opcional - deixe vazio para conteúdo manual",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Conteúdo manual ou gerado pela IA
    content = models.TextField(
        blank=True,
        verbose_name="Conteúdo Manual",
        help_text="Conteúdo direto do post (opcional se usar template)",
    )
    use_markdown = models.BooleanField(
        default=False,
        verbose_name="Usar Markdown",
        help_text="Se marcado, o conteúdo será processado como Markdown",
    )
    generated_content = models.TextField(blank=True, verbose_name="Conteúdo Gerado")
    generated_image_prompt = models.TextField(
        blank=True, verbose_name="Prompt da Imagem"
    )
    generated_image_file = models.ImageField(
        upload_to="generated_images/",
        blank=True,
        null=True,
        verbose_name="Imagem Gerada",
    )

    # Agendamento
    scheduled_time = models.DateTimeField(verbose_name="Horário Agendado")

    # Metadados do post no Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_post_url = models.URLField(blank=True)

    # Logs e erros
    error_message = models.TextField(blank=True)

    # Workflow de aprovação
    requires_approval = models.BooleanField(
        default=False,
        verbose_name="Requer Aprovação",
        help_text="Se marcado, o post precisa ser aprovado antes de publicar",
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_posts",
        verbose_name="Aprovado Por",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Aprovado Em"
    )
    rejection_reason = models.TextField(blank=True, verbose_name="Motivo da Rejeição")

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post Agendado"
        verbose_name_plural = "Posts Agendados"
        ordering = ["-scheduled_time"]

    def __str__(self):
        return (
            f"{self.facebook_page.name} - "
            f"{self.scheduled_time.strftime('%d/%m/%Y %H:%M')}"
        )

    @property
    def is_due(self):
        """Verifica se o post está na hora de ser publicado"""
        return timezone.now() >= self.scheduled_time and self.status == "ready"


class PublishedPost(models.Model):
    """Model para histórico de posts publicados"""

    facebook_page = models.ForeignKey(FacebookPage, on_delete=models.CASCADE)
    scheduled_post = models.OneToOneField(
        ScheduledPost, on_delete=models.CASCADE, null=True, blank=True
    )

    content = models.TextField(verbose_name="Conteúdo Publicado")
    facebook_post_id = models.CharField(max_length=100)
    facebook_post_url = models.URLField(blank=True)
    image_file = models.ImageField(
        upload_to="published_images/",
        blank=True,
        null=True,
        verbose_name="Imagem Publicada",
    )

    # Campos para posts automáticos
    auto_generated = models.BooleanField(
        default=False, verbose_name="Gerado Automaticamente"
    )
    content_type = models.CharField(
        max_length=50, blank=True, verbose_name="Tipo de Conteúdo"
    )
    content_tone = models.CharField(
        max_length=50, blank=True, verbose_name="Tom do Conteúdo"
    )

    # Status para controle
    status = models.CharField(
        max_length=20,
        default="published",
        choices=[
            ("published", "Publicado"),
            ("failed", "Falhou"),
            ("deleted", "Deletado"),
        ],
    )

    # Métricas (podem ser coletadas posteriormente via API)
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)

    published_at = models.DateTimeField(auto_now_add=True)
    metrics_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Post Publicado"
        verbose_name_plural = "Posts Publicados"
        ordering = ["-published_at"]

    def __str__(self):
        return (
            f"{self.facebook_page.name} - "
            f"{self.published_at.strftime('%d/%m/%Y %H:%M')}"
        )


class AIConfiguration(models.Model):
    """Model para configurações da IA"""

    PROVIDER_CHOICES = [
        ("openai", "OpenAI"),
        ("gemini", "Google Gemini"),
    ]

    OPENAI_MODELS = [
        ("gpt-4o", "GPT-4o"),
        ("gpt-4o-mini", "GPT-4o Mini"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
        ("gpt-4", "GPT-4"),
        ("gpt-3.5-turbo", "GPT-3.5 Turbo"),
        ("o1", "O1"),
        ("o1-mini", "O1 Mini"),
    ]

    GEMINI_MODELS = [
        ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("gemini-2.0-flash", "Gemini 2.0 Flash"),
        ("gemini-2.0-flash-exp", "Gemini 2.0 Flash (Experimental)"),
        ("gemini-1.5-flash", "Gemini 1.5 Flash (Legacy)"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro (Legacy)"),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome da Configuração")
    description = models.TextField(blank=True, verbose_name="Descrição")
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default="openai",
        verbose_name="Provedor",
    )
    model = models.CharField(
        max_length=100, default="gpt-3.5-turbo", verbose_name="Modelo da IA"
    )
    max_tokens = models.IntegerField(default=500, verbose_name="Máximo de Tokens")
    temperature = models.FloatField(default=0.7, verbose_name="Temperatura")

    # Configurações específicas para posts
    include_hashtags = models.BooleanField(
        default=True, verbose_name="Incluir Hashtags"
    )
    max_hashtags = models.IntegerField(default=5, verbose_name="Máximo de Hashtags")
    include_emojis = models.BooleanField(default=True, verbose_name="Incluir Emojis")

    is_default = models.BooleanField(default=False, verbose_name="Configuração Padrão")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de IA"
        verbose_name_plural = "Configurações de IA"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Garantir que apenas uma configuração seja padrão
        if self.is_default:
            AIConfiguration.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class PageMetrics(models.Model):
    """Métricas históricas de páginas do Facebook"""

    page = models.ForeignKey(
        FacebookPage,
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name="Página",
    )

    # Métricas da página
    followers_count = models.IntegerField(default=0, verbose_name="Seguidores")
    likes_count = models.IntegerField(default=0, verbose_name="Curtidas")

    # Engagement
    page_impressions = models.IntegerField(
        default=0, verbose_name="Impressões da Página"
    )
    page_impressions_unique = models.IntegerField(
        default=0, verbose_name="Impressões Únicas"
    )
    page_engaged_users = models.IntegerField(
        default=0, verbose_name="Usuários Engajados"
    )
    
    # Alcance segmentado
    page_impressions_paid = models.IntegerField(
        default=0, verbose_name="Impressões Pagas"
    )
    page_impressions_organic = models.IntegerField(
        default=0, verbose_name="Impressões Orgânicas"
    )
    page_impressions_viral = models.IntegerField(
        default=0, verbose_name="Impressões Virais"
    )
    
    # Visualizações
    page_views_total = models.IntegerField(
        default=0, verbose_name="Visualizações Totais"
    )
    page_views_unique = models.IntegerField(
        default=0, verbose_name="Visualizações Únicas"
    )
    
    # Ações na página
    page_post_engagements = models.IntegerField(
        default=0, verbose_name="Engajamentos em Posts"
    )
    page_actions_total = models.IntegerField(
        default=0, verbose_name="Ações Totais"
    )
    page_negative_feedback = models.IntegerField(
        default=0, verbose_name="Feedback Negativo"
    )
    
    # Vídeos
    page_video_views = models.IntegerField(
        default=0, verbose_name="Visualizações de Vídeos"
    )
    
    # Fãs/Seguidores
    page_fan_adds = models.IntegerField(
        default=0, verbose_name="Novos Fãs"
    )
    page_fan_removes = models.IntegerField(
        default=0, verbose_name="Fãs Perdidos"
    )
    
    # Demografia (JSON)
    demographics = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name="Dados Demográficos"
    )

    # Timestamp
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="Coletado em")

    class Meta:
        verbose_name = "Métrica de Página"
        verbose_name_plural = "Métricas de Páginas"
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["page", "-collected_at"]),
        ]

    def __str__(self):
        return f"{self.page.name} - {self.collected_at.strftime('%d/%m/%Y %H:%M')}"


class PostMetrics(models.Model):
    """Métricas históricas de posts publicados"""

    post = models.ForeignKey(
        PublishedPost,
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name="Post",
    )

    # Engagement
    likes_count = models.IntegerField(default=0, verbose_name="Curtidas")
    comments_count = models.IntegerField(default=0, verbose_name="Comentários")
    shares_count = models.IntegerField(default=0, verbose_name="Compartilhamentos")

    # Alcance
    reach = models.IntegerField(default=0, verbose_name="Alcance")
    impressions = models.IntegerField(default=0, verbose_name="Impressões")
    
    # Alcance segmentado
    impressions_paid = models.IntegerField(
        default=0, verbose_name="Impressões Pagas"
    )
    impressions_organic = models.IntegerField(
        default=0, verbose_name="Impressões Orgânicas"
    )
    impressions_viral = models.IntegerField(
        default=0, verbose_name="Impressões Virais"
    )
    impressions_unique = models.IntegerField(
        default=0, verbose_name="Impressões Únicas"
    )

    # Métricas estendidas
    post_clicks = models.IntegerField(default=0, verbose_name="Cliques no Post")
    post_clicks_unique = models.IntegerField(default=0, verbose_name="Cliques Únicos")
    engaged_users = models.IntegerField(
        default=0, verbose_name="Usuários Engajados"
    )
    
    # Vídeo
    video_views = models.IntegerField(default=0, verbose_name="Visualizações de Vídeo")
    video_views_unique = models.IntegerField(
        default=0, verbose_name="Visualizações Únicas"
    )
    
    # Reações
    reactions_count = models.IntegerField(default=0, verbose_name="Total de Reações")
    reactions_by_type = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Reações por Tipo"
    )

    # Engajamento calculado
    engagement_rate = models.FloatField(
        default=0.0, verbose_name="Taxa de Engajamento (%)"
    )

    # Timestamp
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="Coletado em")

    class Meta:
        verbose_name = "Métrica de Post"
        verbose_name_plural = "Métricas de Posts"
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["post", "-collected_at"]),
        ]

    def __str__(self):
        return (
            f"Post {self.post.id} - {self.collected_at.strftime('%d/%m/%Y %H:%M')}"
        )

    def save(self, *args, **kwargs):
        # Calcular taxa de engajamento
        if self.reach > 0:
            total_engagement = (
                self.likes_count + self.comments_count + self.shares_count
            )
            self.engagement_rate = (total_engagement / self.reach) * 100
        super().save(*args, **kwargs)
