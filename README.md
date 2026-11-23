# VYRO AI Content Engine

**Release:** 1.3.0 · **Python:** 3.11+ · **Purpose:** transform validated briefs into production-ready content packages and optional image assets.

## Responsibilities
- Generate hook variants, selected narration, scene plans, shot direction, captions, CTA, and restrained hashtags.
- Produce scene-level `visual_prompt` strings for image generation or human production.
- Preserve source URLs, claims to verify, and rights-aware asset references.
- Optionally generate an image through the official OpenAI Images API when separately configured.
- Keep all generated content in a mandatory human-review state; AI cannot approve its own output.

Voice synthesis is deliberately excluded and belongs to `vyro-ai-voice-studio`. Video rendering belongs to `vyro-video-render-engine`. This service does not publish to Instagram.

## API
- `GET /health`
- `POST /v1/content/generate`
- `POST /v1/images/generate`
- `GET /v1/images/files/{demo_id}/{asset_id}`

All generation/file routes require `Authorization: Bearer $VYRO_SERVICE_API_KEY`.

## Image generation
Set `IMAGE_API_KEY` and `IMAGE_MODEL` to enable optional image generation. The default model is `gpt-image-2.6-flare`. The service accepts only `b64_json` responses, saves files under a hashed demo namespace, and returns an opaque asset ID. Remote image URLs are never fetched. Files expire according to `IMAGE_RETENTION_HOURS` (default 48 hours). Image generation may incur provider charges; leave `IMAGE_API_KEY` blank to keep the feature disabled.

## Install and run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[api,dev]'
uvicorn vyro_ai_content_engine.api:app --host 0.0.0.0 --port 8102
pytest -q
```

## Security and review
- Keep API keys server-side and use HTTPS in production.
- `demo_id` is a temporary namespace, not authentication. Never treat it as a verified identity.
- Source claims, paid-partnership disclosure, AI-media disclosure, and asset rights remain human review items.
- Never invent client results, reviews, product claims, or virality guarantees.

## Image API compatibility

The optional image adapter uses the official OpenAI Images API (`/v1/images/generations`) and requests `b64_json` only. The default `IMAGE_MODEL` is `gpt-image-2.6-flare`; select a model available to the connected API organization. Some GPT Image models may require organization verification. See the official Image API reference and image-generation guide before enabling paid generation.

GPT Image API availability depends on the API organization, model access, account verification requirements, and billing. Keep `IMAGE_API_KEY` empty until the operator has confirmed access and a usage budget; generated images are temporary demo assets, not permanent library files.
