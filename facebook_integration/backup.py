"""
Sistema de backup automático do banco de dados
"""

import logging
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from celery import shared_task

logger = logging.getLogger(__name__)


def get_backup_dir():
    """Retorna o diretório de backup, criando se necessário"""
    backup_dir = getattr(settings, "BACKUP_DIR", settings.BASE_DIR / "backups")
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def generate_backup_filename():
    """Gera nome único para o arquivo de backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"db_backup_{timestamp}.json.gz"


@shared_task
def create_database_backup():
    """
    Cria backup compactado do banco de dados

    Returns:
        dict: Informações sobre o backup criado
    """
    if not getattr(settings, "AUTO_BACKUP_ENABLED", True):
        logger.info("Backup automático desabilitado")
        return {"status": "disabled", "message": "Backup automático está desabilitado"}

    try:
        backup_dir = get_backup_dir()
        filename = generate_backup_filename()
        temp_file = backup_dir / filename.replace(".gz", "")
        final_file = backup_dir / filename

        logger.info(f"Iniciando backup do banco de dados: {filename}")

        # Criar dump do banco usando dumpdata
        with open(temp_file, "w") as f:
            call_command(
                "dumpdata",
                "--exclude",
                "contenttypes",
                "--exclude",
                "auth.permission",
                "--exclude",
                "sessions.session",
                "--indent",
                "2",
                stdout=f,
            )

        # Comprimir o arquivo
        with open(temp_file, "rb") as f_in:
            with gzip.open(final_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remover arquivo temporário
        temp_file.unlink()

        # Obter tamanho do arquivo
        file_size = final_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        logger.info(
            f"Backup criado com sucesso: {filename} " f"({file_size_mb:.2f} MB)"
        )

        # Limpar backups antigos
        cleanup_result = cleanup_old_backups()

        return {
            "status": "success",
            "filename": filename,
            "path": str(final_file),
            "size_mb": round(file_size_mb, 2),
            "timestamp": datetime.now().isoformat(),
            "cleanup": cleanup_result,
        }

    except Exception as e:
        error_msg = f"Erro ao criar backup: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def cleanup_old_backups():
    """
    Remove backups mais antigos que o período de retenção

    Returns:
        dict: Informações sobre a limpeza
    """
    try:
        backup_dir = get_backup_dir()
        retention_days = getattr(settings, "BACKUP_RETENTION_DAYS", 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_count = 0
        deleted_size = 0

        # Listar todos os arquivos de backup
        for backup_file in backup_dir.glob("db_backup_*.json.gz"):
            # Obter data de modificação do arquivo
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)

            if file_time < cutoff_date:
                file_size = backup_file.stat().st_size
                backup_file.unlink()
                deleted_count += 1
                deleted_size += file_size
                logger.info(f"Backup antigo removido: {backup_file.name}")

        if deleted_count > 0:
            deleted_size_mb = deleted_size / (1024 * 1024)
            logger.info(
                f"Limpeza concluída: {deleted_count} backups removidos "
                f"({deleted_size_mb:.2f} MB liberados)"
            )

        return {
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
            "retention_days": retention_days,
        }

    except Exception as e:
        logger.error(f"Erro ao limpar backups antigos: {e}")
        return {"deleted_count": 0, "error": str(e)}


def list_backups():
    """
    Lista todos os backups disponíveis

    Returns:
        list: Lista de backups com informações
    """
    try:
        backup_dir = get_backup_dir()
        backups = []

        for backup_file in sorted(
            backup_dir.glob("db_backup_*.json.gz"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        ):
            file_stat = backup_file.stat()
            file_time = datetime.fromtimestamp(file_stat.st_mtime)

            backups.append(
                {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "created_at": file_time.isoformat(),
                    "age_days": (datetime.now() - file_time).days,
                }
            )

        return backups

    except Exception as e:
        logger.error(f"Erro ao listar backups: {e}")
        return []


def restore_from_backup(backup_path):
    """
    Restaura o banco de dados a partir de um backup

    Args:
        backup_path: Caminho para o arquivo de backup

    Returns:
        dict: Resultado da restauração
    """
    try:
        backup_file = Path(backup_path)

        if not backup_file.exists():
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {backup_path}")

        logger.info(f"Iniciando restauração do backup: {backup_file.name}")

        # Descomprimir arquivo temporariamente
        temp_file = backup_file.parent / backup_file.name.replace(".gz", "")

        with gzip.open(backup_file, "rb") as f_in:
            with open(temp_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Restaurar dados usando loaddata
        with open(temp_file, "r") as f:
            call_command("loaddata", temp_file)

        # Remover arquivo temporário
        temp_file.unlink()

        logger.info(f"Restauração concluída com sucesso: {backup_file.name}")

        return {
            "status": "success",
            "message": f"Banco restaurado do backup: {backup_file.name}",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        error_msg = f"Erro ao restaurar backup: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def get_backup_status():
    """
    Retorna status geral do sistema de backup

    Returns:
        dict: Informações sobre o sistema de backup
    """
    try:
        backup_dir = get_backup_dir()
        backups = list_backups()

        total_size = sum(b["size_mb"] for b in backups)

        latest_backup = backups[0] if backups else None

        return {
            "enabled": getattr(settings, "AUTO_BACKUP_ENABLED", True),
            "backup_dir": str(backup_dir),
            "retention_days": getattr(settings, "BACKUP_RETENTION_DAYS", 30),
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "latest_backup": latest_backup,
            "backups": backups[:10],  # Últimos 10 backups
        }

    except Exception as e:
        logger.error(f"Erro ao obter status do backup: {e}")
        return {"enabled": False, "error": str(e)}
