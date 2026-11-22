from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

# key_style="endpoint" so routes with path IDs (e.g. /exams/{id}/retry) share one bucket instead of one per URL.
limiter = Limiter(key_func=get_remote_address, key_style="endpoint", enabled=get_settings().rate_limit_enabled)
