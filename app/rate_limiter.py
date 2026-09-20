from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

def _limiter_storage_uri() -> str:

    if not settings.redis_enabled:
        return "memory://"
    auth = ""
    if settings.redis_pwd:
        auth = f"{settings.redis_username or ''}:{settings.redis_pwd}@"
    return f"redis://{auth}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


limiter = Limiter(key_func=get_remote_address,     default_limits=["120/minute"],
storage_uri=_limiter_storage_uri(),    in_memory_fallback_enabled=True,
)
