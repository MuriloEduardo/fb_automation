from django.db import models
from django.utils import timezone


class FacebookGroup(models.Model):
    """Modelo para grupos do Facebook"""
    
    PRIVACY_CHOICES = [
        ('OPEN', 'Público'),
        ('CLOSED', 'Fechado'),
        ('SECRET', 'Secreto'),
    ]
    
    # Identificação do grupo
    group_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Configurações
    privacy = models.CharField(
        max_length=20, 
        choices=PRIVACY_CHOICES, 
        default='CLOSED'
    )
    member_count = models.IntegerField(default=0)
    
    # URLs e mídias
    cover_photo = models.URLField(blank=True, null=True)
    permalink_url = models.URLField(blank=True, null=True)
    
    # Permissões (armazenadas como JSON)
    permissions = models.JSONField(default=dict, blank=True)
    
    # Token de acesso (se houver)
    access_token = models.TextField(blank=True, null=True)
    
    # Páginas que têm acesso a este grupo
    accessible_by_pages = models.ManyToManyField(
        'FacebookPage',
        related_name='accessible_groups',
        blank=True,
    )
    
    # Controle
    is_active = models.BooleanField(default=True)
    can_publish = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-member_count', 'name']
        verbose_name = 'Grupo do Facebook'
        verbose_name_plural = 'Grupos do Facebook'
    
    def __str__(self):
        return f"{self.name} ({self.get_privacy_display()})"
    
    def sync_permissions(self):
        """Atualiza informações de permissões do grupo"""
        # Será implementado no service
        pass
    
    def get_member_count_display(self):
        """Retorna contagem formatada de membros"""
        if self.member_count >= 1000000:
            return f"{self.member_count / 1000000:.1f}M"
        elif self.member_count >= 1000:
            return f"{self.member_count / 1000:.1f}K"
        return str(self.member_count)


class GroupPost(models.Model):
    """Posts publicados em grupos"""
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('published', 'Publicado'),
        ('failed', 'Falhou'),
        ('deleted', 'Deletado'),
    ]
    
    # Relações
    group = models.ForeignKey(
        FacebookGroup,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    page = models.ForeignKey(
        'FacebookPage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_posts',
        help_text='Página que publicou (se aplicável)'
    )
    
    # Identificação no Facebook
    post_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Conteúdo
    message = models.TextField()
    link = models.URLField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='published'
    )
    
    # Métricas
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    
    # Timestamps
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Post de Grupo'
        verbose_name_plural = 'Posts de Grupos'
    
    def __str__(self):
        return f"{self.group.name} - {self.published_at.strftime('%d/%m/%Y')}"
