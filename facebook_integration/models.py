from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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

    # Agendamento
    scheduled_time = models.DateTimeField(verbose_name="Horário Agendado")

    # Metadados do post no Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_post_url = models.URLField(blank=True)

    # Logs e erros
    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post Agendado"
        verbose_name_plural = "Posts Agendados"
        ordering = ["-scheduled_time"]

    def __str__(self):
        return f"{self.facebook_page.name} - {self.scheduled_time.strftime('%d/%m/%Y %H:%M')}"

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
    facebook_post_url = models.URLField()

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
        return f"{self.facebook_page.name} - {self.published_at.strftime('%d/%m/%Y %H:%M')}"


class AIConfiguration(models.Model):
    """Model para configurações da IA"""

    name = models.CharField(max_length=255, verbose_name="Nome da Configuração")
    description = models.TextField(blank=True, verbose_name="Descrição")
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
