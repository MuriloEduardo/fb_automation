"""
Sistema de cache Redis para métricas e dados da API do Facebook
"""

import json
import logging
from functools import wraps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# TTLs padrão para diferentes tipos de dados
CACHE_TTL = {
    "page_metrics": 300,  # 5 minutos
    "post_metrics": 300,  # 5 minutos
    "page_info": 1800,  # 30 minutos
    "post_details": 600,  # 10 minutos
    "insights": 900,  # 15 minutos
}


def cache_facebook_api(cache_key_prefix, ttl_key="page_metrics"):
    """
    Decorator para cachear chamadas à API do Facebook

    Args:
        cache_key_prefix: Prefixo para a chave do cache
        ttl_key: Tipo de cache para definir TTL
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Construir chave única baseada nos argumentos
            cache_key = _build_cache_key(cache_key_prefix, args, kwargs)

            # Tentar obter do cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_data

            # Se não está no cache, executar função
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Armazenar no cache
            ttl = CACHE_TTL.get(ttl_key, 300)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")

            return result

        return wrapper

    return decorator


def _build_cache_key(prefix, args, kwargs):
    """Constrói uma chave de cache única"""
    # Ignorar 'self' do primeiro argumento se for método de classe
    cache_args = [str(arg) for arg in args[1:]] if args else []
    cache_kwargs = [f"{k}={v}" for k, v in sorted(kwargs.items())]
    key_parts = [prefix] + cache_args + cache_kwargs
    return ":".join(key_parts)


def invalidate_page_cache(page_id):
    """Invalida todo o cache relacionado a uma página"""
    patterns = [
        f"page_metrics:{page_id}",
        f"page_info:{page_id}",
        f"page_insights:{page_id}",
    ]

    for pattern in patterns:
        cache.delete(pattern)
        logger.info(f"Cache invalidado: {pattern}")


def invalidate_post_cache(post_id):
    """Invalida todo o cache relacionado a um post"""
    patterns = [
        f"post_metrics:{post_id}",
        f"post_details:{post_id}",
        f"post_insights:{post_id}",
    ]

    for pattern in patterns:
        cache.delete(pattern)
        logger.info(f"Cache invalidado: {pattern}")


def get_cache_stats():
    """Retorna estatísticas do cache (se Redis estiver configurado)"""
    try:
        # Tentar obter stats do Redis
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection("default")
        info = redis_conn.info("stats")

        return {
            "backend": "redis",
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "total_keys": redis_conn.dbsize(),
        }
    except Exception as e:
        logger.warning(f"Não foi possível obter stats do cache: {e}")
        return {
            "backend": "default",
            "status": "unavailable",
        }
