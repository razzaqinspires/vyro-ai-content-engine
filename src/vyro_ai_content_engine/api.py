from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .engine import ContentEngine
from .images import ImageGenerationService, ImageProviderError
from .models import ContentBrief

APP_VERSION = "1.3.0"
app = FastAPI(title="VYRO AI Content Engine API", version=APP_VERSION)


def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class ImageJob(BaseModel):
    demo_id: str = Field(pattern=r"^VYRO-DEMO-[A-Fa-f0-9]{8,40}$")
    content_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    prompt: str = Field(min_length=20, max_length=32000)
    size: str = "1024x1024"
    output_format: str = "png"


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-ai-content-engine", "status": "ok", "version": APP_VERSION}


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


@app.post("/v1/images/generate", dependencies=[Depends(require_service_key)])
def generate_image(payload: ImageJob) -> dict[str, Any]:
    service = ImageGenerationService()
    try:
        service.cleanup_expired(int(os.getenv("IMAGE_RETENTION_HOURS", "48")))
        return service.generate(
            demo_id=payload.demo_id, content_id=payload.content_id, prompt=payload.prompt,
            size=payload.size, output_format=payload.output_format,
        )
    except ImageProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/images/files/{demo_id}/{asset_id}", dependencies=[Depends(require_service_key)])
def get_generated_image(demo_id: str, asset_id: str):
    service = ImageGenerationService()
    try:
        path = service.resolve(demo_id, asset_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Akses demo tidak sesuai") from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Image asset tidak ditemukan") from exc
    content_type = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix, "application/octet-stream")
    return FileResponse(path, media_type=content_type, filename=path.name)
