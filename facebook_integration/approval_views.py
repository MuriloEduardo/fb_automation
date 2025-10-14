"""
Views para o sistema de aprovação de posts
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import ScheduledPost, FacebookPage
from .reports import generate_page_pdf_report, generate_consolidated_pdf_report


def is_approver(user):
    """Verifica se o usuário tem permissão para aprovar posts"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_approver)
def approval_queue(request):
    """Lista de posts aguardando aprovação"""
    pending_posts = (
        ScheduledPost.objects.filter(status="pending_approval", requires_approval=True)
        .select_related("facebook_page", "created_by")
        .order_by("scheduled_time")
    )

    context = {"pending_posts": pending_posts, "total_pending": pending_posts.count()}

    return render(request, "facebook_integration/approval_queue.html", context)


@login_required
@user_passes_test(is_approver)
@require_http_methods(["POST"])
def approve_post(request, post_id):
    """Aprova um post"""
    post = get_object_or_404(ScheduledPost, id=post_id)

    if post.status != "pending_approval":
        messages.error(request, "Este post não está aguardando aprovação.")
        return redirect("facebook_integration:approval_queue")

    post.status = "ready"
    post.approved_by = request.user
    post.approved_at = timezone.now()
    post.save()

    messages.success(
        request,
        f'Post aprovado com sucesso! Será publicado em {post.scheduled_time.strftime("%d/%m/%Y %H:%M")}.',
    )

    return redirect("facebook_integration:approval_queue")


@login_required
@user_passes_test(is_approver)
@require_http_methods(["POST"])
def reject_post(request, post_id):
    """Rejeita um post"""
    post = get_object_or_404(ScheduledPost, id=post_id)

    if post.status != "pending_approval":
        messages.error(request, "Este post não está aguardando aprovação.")
        return redirect("facebook_integration:approval_queue")

    rejection_reason = request.POST.get("rejection_reason", "").strip()

    if not rejection_reason:
        messages.error(request, "Por favor, forneça um motivo para a rejeição.")
        return redirect("facebook_integration:approval_queue")

    post.status = "rejected"
    post.rejection_reason = rejection_reason
    post.approved_by = request.user
    post.approved_at = timezone.now()
    post.save()

    messages.warning(request, "Post rejeitado.")

    return redirect("facebook_integration:approval_queue")


@login_required
def preview_post(request, post_id):
    """Preview de um post antes da aprovação"""
    post = get_object_or_404(ScheduledPost, id=post_id)

    context = {"post": post, "can_approve": is_approver(request.user)}

    return render(request, "facebook_integration/post_preview.html", context)


@login_required
@require_http_methods(["POST"])
def request_approval(request, post_id):
    """Solicita aprovação para um post"""
    post = get_object_or_404(ScheduledPost, id=post_id)

    if post.created_by != request.user and not request.user.is_staff:
        messages.error(request, "Você não tem permissão para modificar este post.")
        return redirect("facebook_integration:scheduled_posts")

    if post.status not in ["pending", "ready", "rejected"]:
        messages.error(request, "Este post não pode mais solicitar aprovação.")
        return redirect("facebook_integration:scheduled_posts")

    post.requires_approval = True
    post.status = "pending_approval"
    post.save()

    messages.success(request, "Aprovação solicitada com sucesso.")

    return redirect("facebook_integration:scheduled_posts")


@login_required
def download_page_report(request, page_id):
    """Download de relatório PDF de uma página"""
    page = get_object_or_404(FacebookPage, id=page_id)

    # Obter parâmetros de data
    days = int(request.GET.get("days", 30))
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)

    try:
        # Gerar PDF
        pdf_buffer = generate_page_pdf_report(page_id, start_date, end_date)

        # Preparar response
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        filename = f'relatorio_{page.name.replace(" ", "_")}_{timezone.now().strftime("%Y%m%d")}.pdf'
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Erro ao gerar relatório: {str(e)}")
        return redirect("facebook_integration:dashboard")


@login_required
def download_consolidated_report(request):
    """Download de relatório consolidado"""
    # Obter parâmetros
    days = int(request.GET.get("days", 30))
    page_ids = request.GET.getlist("pages")

    if page_ids:
        page_ids = [int(pid) for pid in page_ids]
    else:
        page_ids = None

    try:
        # Gerar PDF
        pdf_buffer = generate_consolidated_pdf_report(page_ids, days)

        # Preparar response
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        filename = f'relatorio_consolidado_{timezone.now().strftime("%Y%m%d")}.pdf'
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Erro ao gerar relatório: {str(e)}")
        return redirect("facebook_integration:dashboard")


@login_required
def approval_stats(request):
    """Estatísticas do sistema de aprovação"""
    from django.db.models import Count, Q

    stats = ScheduledPost.objects.filter(requires_approval=True).aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending_approval")),
        approved=Count("id", filter=Q(status__in=["ready", "published"])),
        rejected=Count("id", filter=Q(status="rejected")),
    )

    # Posts por aprovador
    approvers = (
        ScheduledPost.objects.filter(requires_approval=True, approved_by__isnull=False)
        .values("approved_by__username")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    context = {
        "stats": stats,
        "approvers": approvers,
    }

    return render(request, "facebook_integration/approval_stats.html", context)
