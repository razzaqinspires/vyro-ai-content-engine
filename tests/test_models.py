import pytest
from pydantic import ValidationError
from vyro_ai_content_engine.models import ContentBrief, ContentPackage


def brief():
    return {
        "content_id":"vyro-test-001","title":"Contoh naskah edukasi","pillar":"education",
        "objective":"Memberi satu tips praktis kepada kreator pemula","audience":"Kreator pemula Indonesia",
        "duration_seconds":30,"hook":"Jangan mulai video dengan cara ini.",
        "narration":"Ini contoh narasi yang cukup panjang untuk validasi naskah video pendek.",
        "call_to_action":"Simpan tips ini."
    }


def test_brief_validates():
    assert ContentBrief.model_validate(brief()).content_id == "vyro-test-001"


def test_path_traversal_rejected():
    data = brief(); data["content_id"] = "../bad"
    with pytest.raises(ValidationError): ContentBrief.model_validate(data)


def test_package_requires_human_review():
    data = {
      "content_id":"vyro-test-001","title":"Test","pillar":"education","audience":"new creators",
      "platform":"instagram_reels","language":"id-ID","duration_seconds":20,
      "hook_variants":["hook a","hook b"],"selected_hook":"hook a","narration":"A sufficiently long narration for package validation.",
      "scenes":[{"scene_number":1,"duration_seconds":10,"visual_direction":"Phone shot of a creator speaking","on_screen_text":"First point","voiceover":"Spoken line"},
                {"scene_number":2,"duration_seconds":10,"visual_direction":"Closeup of the product","on_screen_text":"Second point","voiceover":"Another spoken line"}],
      "caption":"Caption","hashtags":[],"call_to_action":"Follow","source_urls":[],"claims_to_verify":[],"review_flags":[],"human_review_required":False
    }
    with pytest.raises(ValidationError): ContentPackage.model_validate(data)
