#!/bin/bash
# Helper script para novas funcionalidades do sistema

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  FB Automation - System Management    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

function test_all() {
    print_header
    echo "🧪 Testando todos os componentes..."
    echo ""
    python manage.py test_system --component=all
}

function test_cache() {
    print_header
    echo "📦 Testando Cache Redis..."
    echo ""
    python manage.py test_system --component=cache
}

function test_email() {
    print_header
    echo "📧 Testando Email..."
    echo ""
    python manage.py test_system --component=email
}

function test_backup() {
    print_header
    echo "💾 Testando Backup..."
    echo ""
    python manage.py test_system --component=backup
}

function create_backup() {
    print_header
    echo "💾 Criando backup do banco de dados..."
    echo ""
    
    python manage.py shell << EOF
from facebook_integration.backup import create_database_backup
import json

result = create_database_backup()
print(json.dumps(result, indent=2))
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Backup criado com sucesso!"
        echo ""
        list_backups
    else
        print_error "Erro ao criar backup"
    fi
}

function list_backups() {
    print_header
    echo "📋 Listando backups disponíveis..."
    echo ""
    
    python manage.py shell << EOF
from facebook_integration.backup import list_backups

backups = list_backups()

if not backups:
    print("Nenhum backup encontrado.")
else:
    print(f"{'Arquivo':<35} {'Tamanho':<10} {'Idade':<12} {'Data':<20}")
    print("-" * 80)
    for backup in backups:
        print(f"{backup['filename']:<35} {backup['size_mb']:<8} MB {backup['age_days']:<10}d {backup['created_at'][:19]}")
    print("")
    print(f"Total: {len(backups)} backups")
EOF
}

function backup_status() {
    print_header
    echo "📊 Status do sistema de backup..."
    echo ""
    
    python manage.py shell << EOF
from facebook_integration.backup import get_backup_status
import json

status = get_backup_status()
print(json.dumps(status, indent=2))
EOF
}

function cache_stats() {
    print_header
    echo "📊 Estatísticas do cache..."
    echo ""
    
    python manage.py shell << EOF
from facebook_integration.cache import get_cache_stats
import json

stats = get_cache_stats()
print(json.dumps(stats, indent=2))

# Calcular hit rate se possível
if 'hits' in stats and 'misses' in stats:
    total = stats['hits'] + stats['misses']
    if total > 0:
        hit_rate = (stats['hits'] / total) * 100
        print(f"\nHit Rate: {hit_rate:.2f}%")
EOF
}

function invalidate_cache() {
    print_header
    echo "🧹 Limpando cache..."
    echo ""
    
    python manage.py shell << EOF
from django.core.cache import cache

cache.clear()
print("Cache limpo com sucesso!")
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Cache invalidado"
    else
        print_error "Erro ao invalidar cache"
    fi
}

function check_celery() {
    print_header
    echo "🔍 Verificando status do Celery..."
    echo ""
    
    # Verificar se Celery está rodando
    if pgrep -f "celery.*worker" > /dev/null; then
        print_success "Celery Worker está rodando"
    else
        print_warning "Celery Worker não encontrado"
    fi
    
    if pgrep -f "celery.*beat" > /dev/null; then
        print_success "Celery Beat está rodando"
    else
        print_warning "Celery Beat não encontrado"
    fi
    
    echo ""
    print_info "Tasks agendadas no Celery Beat:"
    python manage.py shell << EOF
from django_celery_beat.models import PeriodicTask

tasks = PeriodicTask.objects.all()
if tasks:
    for task in tasks:
        status = "✓ Ativo" if task.enabled else "✗ Desabilitado"
        print(f"  {status:<15} {task.name}")
else:
    print("  Nenhuma task agendada")
EOF
}

function show_help() {
    print_header
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponíveis:"
    echo ""
    echo "  ${GREEN}test${NC}"
    echo "    test-all           Testa todos os componentes"
    echo "    test-cache         Testa cache Redis"
    echo "    test-email         Testa configuração de email"
    echo "    test-backup        Testa sistema de backup"
    echo ""
    echo "  ${GREEN}backup${NC}"
    echo "    backup-create      Cria um novo backup"
    echo "    backup-list        Lista todos os backups"
    echo "    backup-status      Mostra status do sistema"
    echo ""
    echo "  ${GREEN}cache${NC}"
    echo "    cache-stats        Mostra estatísticas do cache"
    echo "    cache-clear        Limpa todo o cache"
    echo ""
    echo "  ${GREEN}celery${NC}"
    echo "    celery-status      Verifica status do Celery"
    echo ""
    echo "  ${GREEN}help${NC}               Mostra esta ajuda"
    echo ""
}

# Main
case "${1:-help}" in
    test-all)
        test_all
        ;;
    test-cache)
        test_cache
        ;;
    test-email)
        test_email
        ;;
    test-backup)
        test_backup
        ;;
    backup-create)
        create_backup
        ;;
    backup-list)
        list_backups
        ;;
    backup-status)
        backup_status
        ;;
    cache-stats)
        cache_stats
        ;;
    cache-clear)
        invalidate_cache
        ;;
    celery-status)
        check_celery
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Comando desconhecido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
