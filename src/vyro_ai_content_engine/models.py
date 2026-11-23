from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Severity = Literal["info", "warning", "blocking"]


class AssetReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    asset_id: str | None = Field(default=None, min_length=3, max_length=120)
    path_or_url: str = Field(min_length=1, max_length=2048)
    media_type: Literal["image", "video", "audio"]
    rights_confirmed: bool = False
    attribution: str | None = Field(default=None, max_length=500)
    source: Literal["library", "user_upload", "licensed_stock", "generated"] = "user_upload"


class ReviewFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=2, max_length=60)
    severity: Severity
    message: str = Field(min_length=4, max_length=500)


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_number: int = Field(ge=1, le=20)
    duration_seconds: float = Field(gt=0, le=45)
    visual_direction: str = Field(min_length=5, max_length=700)
    visual_prompt: str = Field(default="", max_length=4000)
    visual_style: str = Field(default="", max_length=500)
    on_screen_text: str = Field(min_length=1, max_length=140)
    voiceover: str = Field(default="", max_length=900)
    asset_hint: str | None = Field(default=None, max_length=300)
    asset_rationale: str | None = Field(default=None, max_length=500)
    transition: str | None = Field(default=None, max_length=100)


class ContentBrief(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: str = "1.2"
    content_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    title: str = Field(min_length=5, max_length=140)
    pillar: str = Field(min_length=2, max_length=80)
    objective: str = Field(min_length=10, max_length=500)
    audience: str = Field(min_length=5, max_length=300)
    platform: str = Field(default="instagram_reels", max_length=50)
    language: str = Field(default="id-ID", max_length=20)
    duration_seconds: int = Field(default=30, ge=8, le=90)
    hook: str = Field(min_length=8, max_length=240)
    narration: str = Field(min_length=20, max_length=5000)
    call_to_action: str = Field(min_length=3, max_length=300)
    caption: str | None = Field(default=None, max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    claims_to_verify: list[str] = Field(default_factory=list, max_length=20)
    assets: list[AssetReference] = Field(default_factory=list, max_length=30)
    reference_asset_ids: list[str] = Field(default_factory=list, max_length=30)
    brand_voice: str = Field(default="jelas, natural, profesional, tidak clickbait", max_length=500)
    visual_style: str = Field(default="VYRO MEDIA: black, white, neon lime, diagonal, cinematic", max_length=500)
    template_id: str | None = Field(default=None, max_length=120)
    paid_partnership: bool = False
    ai_generated_media: bool = False
    human_review_required: bool = True
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("content_id")
    @classmethod
    def safe_id(cls, value: str) -> str:
        if ".." in value or value.startswith("."):
            raise ValueError("content_id tidak boleh berupa path traversal")
        return value

    @field_validator("hashtags")
    @classmethod
    def normalize_hashtags(cls, values: list[str]) -> list[str]:
        import re
        cleaned = []
        for value in values:
            tag = value.strip().lstrip("#")
            if tag and re.fullmatch(r"[A-Za-z0-9_]{1,50}", tag):
                cleaned.append(tag)
        return list(dict.fromkeys(cleaned))[:8]

    @model_validator(mode="after")
    def enforce_review_gate(self):
        if not self.human_review_required:
            raise ValueError("human_review_required must remain true")
        return self


class ContentPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.3"
    content_id: str = Field(min_length=4, max_length=80)
    title: str
    pillar: str
    audience: str
    platform: str = "instagram_reels"
    language: str = "id-ID"
    duration_seconds: int = Field(ge=8, le=90)
    hook_variants: list[str] = Field(min_length=2, max_length=5)
    selected_hook: str
    narration: str = Field(min_length=20, max_length=5000)
    scenes: list[Scene] = Field(min_length=2, max_length=12)
    caption: str = Field(min_length=1, max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=8)
    call_to_action: str
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    claims_to_verify: list[str] = Field(default_factory=list, max_length=20)
    assets: list[AssetReference] = Field(default_factory=list, max_length=30)
    visual_style: str = Field(default="", max_length=500)
    review_flags: list[ReviewFlag] = Field(default_factory=list, max_length=30)
    human_review_required: bool = True
    review_approved: bool = False

    @model_validator(mode="after")
    def validate_scene_sequence(self):
        numbers = [scene.scene_number for scene in self.scenes]
        if numbers != sorted(numbers) or len(set(numbers)) != len(numbers):
            raise ValueError("Nomor scene harus berurutan dan unik")
        total = sum(scene.duration_seconds for scene in self.scenes)
        if total > self.duration_seconds * 1.35:
            raise ValueError("Total durasi scene melebihi toleransi 135%")
        if not self.human_review_required:
            raise ValueError("human_review_required harus selalu true")
        if self.review_approved:
            raise ValueError("AI tidak boleh menyetujui content package sendiri")
        return self
