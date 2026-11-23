from vyro_ai_content_engine.models import ContentBrief, ContentPackage


def make_brief():
    return ContentBrief(
        content_id="vyro-content-001", title="Tips konten promosi untuk UMKM", pillar="brand_promotion",
        objective="Membantu UMKM membuat konten promosi yang jelas", audience="Pemilik UMKM Indonesia",
        hook="Produk baik perlu ditampilkan dengan jelas", narration="Tampilkan satu keunggulan produk yang benar dan mudah dipahami penonton.",
        call_to_action="Simpan ide ini untuk konten berikutnya.",
    )


def test_brief_exposes_visual_direction():
    brief = make_brief()
    assert "VYRO MEDIA" in brief.visual_style
    assert brief.human_review_required is True


def test_content_package_cannot_self_approve():
    data = {
        "content_id": "vyro-content-001", "title": "Tips konten promosi", "pillar": "brand_promotion",
        "audience": "Pemilik UMKM", "duration_seconds": 20, "hook_variants": ["Hook A", "Hook B"],
        "selected_hook": "Hook A", "narration": "Narasi yang cukup panjang untuk sebuah konten singkat.",
        "scenes": [{"scene_number": 1, "duration_seconds": 10, "visual_direction": "Close up produk di meja", "on_screen_text": "Produk unggulan", "visual_prompt": "Cinematic close up product shot"},
                   {"scene_number": 2, "duration_seconds": 10, "visual_direction": "Pemilik usaha menjelaskan", "on_screen_text": "Kenali manfaatnya", "visual_prompt": "Warm documentary portrait"}],
        "caption": "Konten promosi yang jelas.", "call_to_action": "Simpan konten ini.", "review_approved": True,
    }
    try:
        ContentPackage.model_validate(data)
    except Exception:
        return
    raise AssertionError("AI package must never self-approve")


def test_content_brief_accepts_template_and_asset_context():
    from vyro_ai_content_engine.models import AssetReference
    brief = ContentBrief.model_validate(make_brief().model_dump() | {
        "reference_asset_ids": ["asset-logo-main"],
        "template_id": "photo_01_product_spotlight",
        "assets": [AssetReference(asset_id="asset-001", path_or_url="/library/photo.png", media_type="image", rights_confirmed=True, source="library")],
    })
    assert brief.reference_asset_ids == ["asset-logo-main"]
    assert brief.assets[0].rights_confirmed is True


def test_content_package_scene_accepts_visual_prompt():
    data = {
        "content_id": "vyro-content-001", "title": "Tips konten promosi", "pillar": "brand_promotion",
        "audience": "Pemilik UMKM", "duration_seconds": 20, "hook_variants": ["Hook A", "Hook B"],
        "selected_hook": "Hook A", "narration": "Narasi cukup panjang untuk konten singkat dan mudah dipahami.",
        "scenes": [
            {"scene_number": 1, "duration_seconds": 10, "visual_direction": "Close up produk di meja", "on_screen_text": "Produk unggulan", "visual_prompt": "Macro product photo, dramatic softbox, black lime set"},
            {"scene_number": 2, "duration_seconds": 10, "visual_direction": "Pemilik usaha menjelaskan", "on_screen_text": "Kenali manfaatnya", "visual_prompt": "Documentary portrait, natural window light"}
        ],
        "caption": "Konten promosi yang jelas.", "call_to_action": "Simpan konten ini."
    }
    package = ContentPackage.model_validate(data)
    assert package.scenes[0].visual_prompt.startswith("Macro product")
    assert package.review_approved is False
