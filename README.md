# VYRO AI Content Engine

**Version:** 1.1.0  
**Role:** Transform a validated content brief into a review-ready, structured production package.  
**Boundary:** This repository generates content strategy, scripts, hooks, scene plans, on-screen text, captions, and voiceover *text*. It does **not** synthesize audio, render video, schedule posts, or publish.

## What changed in 1.1.0

- Clearly separated AI voice generation into the independent `vyro-ai-voice-studio` repository.
- Strengthened brief and output contracts with bounded text, scene, and hashtag fields.
- Added claim traceability, editorial review flags, brand-safety reminders, and a mandatory human-approval state.
- Added provider retry/backoff, configurable timeouts, strict JSON parsing, and request IDs.
- Added a stable integration contract: `ContentPackage` JSON with `content_id` unchanged end-to-end.

## Pipeline

1. Validate the incoming brief.
2. Normalize objective, audience, platform, content pillar, and source/claim metadata.
3. Generate hook variants and select a candidate.
4. Draft narration and a scene-by-scene storyboard.
5. Produce on-screen text, shot direction, and voiceover *text* for each scene.
6. Generate caption, relevant hashtags, CTA, and editorial flags.
7. Validate structured output and preserve content identity.
8. Export a package marked `human_review_required=true`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Add an OpenAI-compatible provider key to `.env`. Do not commit `.env`.

## CLI

```bash
vyro-ai validate examples/brief_umkm.json
vyro-ai generate examples/brief_umkm.json --output output/content-package.json
```

## Python API

```python
from vyro_ai_content_engine.engine import ContentEngine

engine = ContentEngine.from_env()
package = engine.generate(brief_dict)
content_package = package.model_dump(mode="json")
```

The returned `ContentPackage` can be passed to `vyro-ai-voice-studio` after an editor has checked it and explicitly sets `review_approved=true`, using its `narration` or scene-level `voiceover` values. See `docs/INTEGRATION_CONTRACT.md` in the upgrade bundle.

## Editorial controls

- Brief text is untrusted input and cannot override system instructions.
- The model must not fabricate news, statistics, source URLs, testimonials, product outcomes, or guaranteed virality.
- `source_urls` and `claims_to_verify` are preserved. Any new material claims are added to `claims_to_verify`.
- Paid partnership and AI-generated media reminders are surfaced as review flags.
- No generated result is considered approved solely because it passed schema validation.

## Quality checks

```bash
ruff check .
ruff format --check .
pytest
```

## Supported use

Designed for VYRO MEDIA's Indonesian short-form editorial workflow. Provider-neutral in the sense that any endpoint implementing the OpenAI-compatible Chat Completions JSON response contract can be configured.
