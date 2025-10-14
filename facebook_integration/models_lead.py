from django.db import models


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
