from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import ValidationError

from .engine import ContentEngine
from .models import ContentBrief

app = FastAPI(title="VYRO AI Content Engine API", version="1.2.0")

def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-ai-content-engine", "status": "ok", "version": "1.2.0"}

@app.post("/v1/content/generate", dependencies=[Depends(require_service_key)])
def generate_content(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        brief = ContentBrief.model_validate(payload)
        package = ContentEngine.from_env().generate(brief)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = package.model_dump(mode="json")
    result["human_review_required"] = True
    result["review_approved"] = False
    return result
