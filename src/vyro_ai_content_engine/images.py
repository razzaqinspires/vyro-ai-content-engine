from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


class ImageProviderError(RuntimeError):
    pass


class ImageGenerationService:
    """Optional GPT Image API adapter. Generated files are isolated by browser demo ID."""

    ALLOWED_SIZES = {"1024x1024", "1024x1536", "1536x1024"}
    ALLOWED_FORMATS = {"png", "jpeg", "webp"}

    def __init__(self):
        self.api_key = os.getenv("IMAGE_API_KEY") or os.getenv("AI_API_KEY", "")
        self.base_url = os.getenv("IMAGE_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("IMAGE_MODEL", "gpt-image-2.6-flare")
        self.timeout = max(30, min(int(os.getenv("IMAGE_TIMEOUT_SECONDS", "180")), 600))
        self.output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", "./image_outputs")).expanduser().resolve()
        self.max_bytes = max(1024 * 1024, min(int(os.getenv("IMAGE_MAX_OUTPUT_BYTES", str(20 * 1024 * 1024))), 40 * 1024 * 1024))

    @staticmethod
    def _demo_namespace(demo_id: str) -> str:
        if not re.fullmatch(r"VYRO-DEMO-[A-F0-9]{8,40}", demo_id.upper()):
            raise ValueError("demo_id tidak valid")
        return hashlib.sha256(demo_id.upper().encode()).hexdigest()[:24]

    def generate(self, *, demo_id: str, content_id: str, prompt: str, size: str = "1024x1024", output_format: str = "png") -> dict:
        if not self.api_key:
            raise ImageProviderError("IMAGE_API_KEY belum dikonfigurasi; fitur AI Image sedang nonaktif")
        if not self.base_url.startswith("https://"):
            raise ValueError("IMAGE_API_BASE_URL wajib HTTPS")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", content_id) or ".." in content_id:
            raise ValueError("content_id tidak valid")
        if not 20 <= len(prompt.strip()) <= 32000:
            raise ValueError("Prompt gambar harus 20–32.000 karakter")
        if size not in self.ALLOWED_SIZES or output_format not in self.ALLOWED_FORMATS:
            raise ValueError("Ukuran atau format gambar tidak diizinkan")

        payload = {
            "model": self.model, "prompt": prompt.strip(), "n": 1,
            "size": size, "quality": os.getenv("IMAGE_QUALITY", "medium"),
            "output_format": output_format, "background": "opaque",
        }
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=20)) as client:
                response = client.post(
                    f"{self.base_url}/images/generations",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            item = (body.get("data") or [])[0]
            encoded = item.get("b64_json")
            if not encoded:
                raise ImageProviderError("Provider tidak mengembalikan b64_json; URL eksternal tidak diterima")
            content = base64.b64decode(encoded, validate=True)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            raise ImageProviderError(f"Image provider gagal: {type(exc).__name__}") from exc
        if not content or len(content) > self.max_bytes:
            raise ImageProviderError("Ukuran hasil gambar kosong atau melewati IMAGE_MAX_OUTPUT_BYTES")

        ext = "jpg" if output_format == "jpeg" else output_format
        magic = {"png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff", "webp": b"RIFF"}
        if not content.startswith(magic[ext]):
            raise ImageProviderError("Signature file hasil provider tidak cocok dengan format yang diminta")
        namespace = self._demo_namespace(demo_id)
        asset_id = uuid.uuid4().hex
        folder = self.output_dir / namespace / content_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{asset_id}.{ext}"
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_bytes(content)
        temp.replace(target)
        manifest = {
            "asset_id": asset_id, "content_id": content_id, "demo_namespace": namespace,
            "filename": target.name, "format": output_format, "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "model": self.model,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(), "human_review_required": True,
        }
        target.with_suffix(target.suffix + ".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {**manifest, "download_path": f"/v1/images/files/{demo_id}/{asset_id}"}

    def resolve(self, demo_id: str, asset_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", asset_id):
            raise ValueError("asset_id tidak valid")
        namespace = self._demo_namespace(demo_id)
        folder = self.output_dir / namespace
        matches = list(folder.glob(f"*/{asset_id}.*")) if folder.exists() else []
        matches = [p for p in matches if not p.name.endswith(".json") and not p.name.endswith(".tmp")]
        if len(matches) != 1 or not matches[0].is_file():
            raise FileNotFoundError("Image asset tidak ditemukan")
        meta_path = matches[0].with_suffix(matches[0].suffix + ".json")
        if not meta_path.is_file():
            raise FileNotFoundError("Image manifest tidak ditemukan")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata.get("demo_namespace") != namespace or metadata.get("asset_id") != asset_id:
            raise PermissionError("Image asset bukan milik demo ini")
        return matches[0]

    def cleanup_expired(self, retention_hours: int = 48) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, retention_hours))
        removed = 0
        if not self.output_dir.exists():
            return removed
        for manifest_path in self.output_dir.glob("*/*/*.json"):
            try:
                metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
                created = datetime.fromisoformat(metadata["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    image_path = manifest_path.with_suffix("")
                    image_path.unlink(missing_ok=True)
                    manifest_path.unlink(missing_ok=True)
                    removed += 1
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
        return removed
