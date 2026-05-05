import hmac
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_header = APIKeyHeader(name="X-Api-Key", auto_error=True)


def validate_api_key(provided: str = Security(_header)) -> str:
    from app.config import settings
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API key not configured on server")
    if not hmac.compare_digest(provided.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return provided
